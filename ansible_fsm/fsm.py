

import gevent
from gevent.queue import PriorityQueue, Queue
from pprint import pformat

from .conf import settings
from . import messages
from ansible_task_worker.worker import AnsibleTaskWorker
from ansible_task_worker.messages import Task, Inventory, TaskComplete, RunnerMessage, ShutdownRequested, ShutdownComplete
import logging

logger = logging.getLogger('ansible_fsm.fsm')

NULL_EVENT = messages.Event(0, 0, 'null', {})

DEFAULT_OUTPUT = 'default'


class _Channel(object):

    def __init__(self, from_fsm, to_fsm, tracer, queue=None):
        if queue is None:
            self.queue = PriorityQueue()
        else:
            self.queue = queue
        self.from_fsm = from_fsm
        self.to_fsm = to_fsm
        self.tracer = tracer

    def put(self, priority_order_item):
        priority, order, item = priority_order_item
        self.tracer.send_trace_message(messages.ChannelTrace(self.tracer.trace_order_seq(),
                                                             self.from_fsm.fsm_id if self.from_fsm else None,
                                                             self.to_fsm.fsm_id if self.to_fsm else None,
                                                             item.name))
        self.queue.put(priority_order_item)

    def get(self, block=True, timeout=None):
        return self.queue.get(block, timeout)

    receive = get


def Channel(from_fsm, to_fsm, tracer, queue=None):
    if settings.instrumented:
        return _Channel(from_fsm, to_fsm, tracer, queue)
    if queue is not None:
        return queue
    else:
        return PriorityQueue()


class _NullChannel(object):

    def __init__(self):
        pass

    def put(self, item):
        pass


NullChannelSingleton = _NullChannel()


class _NullChannelInstrumented(object):

    def __init__(self, from_fsm, tracer):
        self.from_fsm = from_fsm
        self.tracer = tracer

    def put(self, item):
        self.tracer.send_trace_message(messages.ChannelTrace(self.tracer.trace_order_seq(),
                                                             self.from_fsm.fsm_id,
                                                             None,
                                                             item.name))


def NullChannel(from_fsm, tracer):

    if settings.instrumented:
        return _NullChannelInstrumented(from_fsm, tracer)
    else:
        return NullChannelSingleton


class FSMController(object):

    def __init__(self, name, fsm_id, states, initial_state, tracer, channel_tracer, fsm_registry, fsm_id_seq, inventory, play_header, outputs):
        self.shutting_down = False
        self.is_shutdown = False
        self.fsm_registry = fsm_registry
        self.name = name
        self.fsm_id = fsm_id
        self.tracer = tracer
        self.channel_tracer = channel_tracer
        self.state = initial_state
        self.states = states
        self.inbox = PriorityQueue()
        self.self_channel = Channel(self, self, tracer, self.inbox)
        self.worker = AnsibleTaskWorker(tracer, next(fsm_id_seq), inventory, play_header)
        self.worker_output_queue = Queue()
        self.worker.controller.outboxes['output'] = self.worker_output_queue
        self.worker.queue.put(Inventory(0, inventory))
        self.outboxes = dict(default=None)
        if outputs:
            self.outboxes.update({name: None for name in outputs})
        self.thread = gevent.spawn(self.receive_messages)

    def enter(self):
        self.state.exec_handler(self, 'enter', NULL_EVENT)

    def change_state(self, state, handling_message_type):
        if self.state:
            self.state.exec_handler(self, 'exit', NULL_EVENT)
        if settings.instrumented:
            self.tracer.send_trace_message(messages.FSMTrace(self.tracer.trace_order_seq(),
                                                             self.name,
                                                             self.fsm_id,
                                                             self.state.name,
                                                             state.name,
                                                             handling_message_type))
        self.state = state
        if self.state:
            self.state.exec_handler(self, 'enter', NULL_EVENT)

    def handle_message(self, message_type, message):
        self.state.exec_handler(self, message_type, message)

    def shutdown(self):
        self.shutting_down = True
        if self.is_shutdown:
            return
        self.worker.queue.put(ShutdownRequested())
        for _ in range(10):
            gevent.sleep(1)
            worker_message = self.worker_output_queue.get()
            if isinstance(worker_message, ShutdownComplete):
                break
        self.is_shutdown = True

    def receive_messages(self):

        while not self.shutting_down:
            gevent.sleep(0.1)
            logger.info("Waiting for messages")
            priority, order, message = self.inbox.get()
            if self.shutting_down:
                logger.info("Ignoring message due to shutdown")
                break
            message_type = message.name
            if message_type == 'Shutdown':
                logger.info("Shutting down")
                self.shutdown()
                break
            elif message_type == 'ChangeState' and self.state.name != message.data['current_state']:
                logger.info("Ignoring ChangeState message because the current state does not match")
            elif message_type == 'ChangeState' and self.state.name == message.data['current_state']:
                logger.info("Changing state")
                self.change_state(self.states[message.data['next_state']],
                                  message.data['handling_message_type'])
            else:
                logger.info("Handling message {}".format(message_type))
                self.handle_message(message_type, message)


FSM_TASKS = ['change_state', 'shutdown', 'send_event']


class State(object):

    def __init__(self, name, handlers):
        self.name = name
        self.handlers = handlers

    def call_set_fact(self, controller, message):
        controller.worker.queue.put(Task(0, 0, [dict(set_fact=dict(cacheable=True,
                                                                   event=message.data))]))
        while True:
            worker_message = controller.worker_output_queue.get()
            if isinstance(worker_message, TaskComplete):
                break

    def call_when(self, controller, task):
        controller.worker.queue.put(Task(0, 0, [dict(when_helper=None,
                                                     when=task['when'])]))
        while True:
            worker_message = controller.worker_output_queue.get()
            if isinstance(worker_message, RunnerMessage):
                if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                    pass
                elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                    pass
                elif worker_message.data.get('event') == 'runner_on_skipped':
                    return False
                elif worker_message.data.get('event') == 'runner_on_ok':
                    return True

    def exec_handler(self, controller, msg_type, message):
        if msg_type in self.handlers:
            if message.data:
                self.call_set_fact(controller, message)
            for task_id, task in enumerate(self.handlers[msg_type]):
                task_failed = False
                found_special_handler = False
                for cmd in FSM_TASKS:
                    # task is a dict
                    if cmd in task:
                        found_special_handler = True
                        special_handler = getattr(self, 'handle_' + cmd)
                        special_handler(controller, task, msg_type)
                        break
                if not found_special_handler:
                    controller.worker.queue.put(Task(task_id, 0, [task]))
                    while True:
                        worker_message = controller.worker_output_queue.get()
                        if isinstance(worker_message, RunnerMessage):
                            if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                                pass
                            elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                                pass
                            else:
                                if worker_message.data.get('event') == 'runner_on_failed':
                                    task_failed = True
                        elif isinstance(worker_message, TaskComplete):
                            if task_failed:
                                self.exec_handler(controller, 'failure', NULL_EVENT)
                                return
                            else:
                                break
                        else:
                            logger.info("unhandled: %s", pformat(worker_message))

    def handle_change_state(self, controller, task, msg_type):
        if 'when' in task:
            if not self.call_when(controller, task):
                return
        controller.self_channel.put((0, 0, messages.Event(controller.fsm_id,
                                                          controller.fsm_id,
                                                          'ChangeState',
                                                          dict(current_state=self.name,
                                                               next_state=task['change_state'],
                                                               handling_message_type=msg_type))))

    def handle_shutdown(self, controller, task, msg_type):
        controller.self_channel.put((0, 0, messages.Event(controller.fsm_id,
                                                          controller.fsm_id,
                                                          'Shutdown',
                                                          dict(handling_message_type=msg_type))))

    def handle_send_event(self, controller, task, msg_type):
        send_event = task['send_event']

        # Find the destination FSM to send the event to
        # First check for the FSM name in the send_event task
        # Second check for a mapping of the outboxes to FSMs
        # Third use the default mapping
        # If no FSM is found send no event.

        logger.info(send_event)
        logger.info(controller.outboxes)

        if 'fsm' in send_event:
            to_fsm_id = send_event['fsm']
        elif 'output' in send_event:
            to_fsm_id = controller.outboxes.get(send_event['output'], None)
        else:
            to_fsm_id = controller.outboxes.get(DEFAULT_OUTPUT, None)

        if to_fsm_id is None:
            logger.info("Dropping event %s", send_event['name'])
            return

        logger.info("Sending to fsm %s", to_fsm_id)

        send_event_task = [dict(send_event=dict(event=send_event['name'],
                                                data=send_event.get('data', {}),
                                                to_fsm=to_fsm_id,
                                                from_fsm=controller.name,
                                                host='127.0.0.1',
                                                port=controller.control_socket_port))]
        if 'when' in task:
            send_event_task[0]['when'] = task['when']
        if 'with_items' in task:
            send_event_task[0]['with_items'] = task['with_items']

        controller.worker.queue.put(Task(0, 0, send_event_task))
        while True:
            worker_message = controller.worker_output_queue.get()
            if isinstance(worker_message, RunnerMessage):
                if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                    pass
                elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                    pass
                elif worker_message.data.get('event') == 'runner_on_skipped':
                    return
                elif worker_message.data.get('event') == 'runner_on_ok':
                    return


class _NullTracer(object):

    def trace_order_seq(self):
        return 0

    def send_trace_message(self, message):
        pass


NullTracer = _NullTracer()
