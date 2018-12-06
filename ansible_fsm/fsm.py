

import gevent
from gevent.queue import Queue

from .conf import settings
from . import messages


class _Channel(object):

    def __init__(self, from_fsm, to_fsm, tracer, queue=None):
        if queue is None:
            self.queue = Queue()
        else:
            self.queue = queue
        self.from_fsm = from_fsm
        self.to_fsm = to_fsm
        self.tracer = tracer

    def put(self, item):
        self.tracer.send_trace_message(messages.ChannelTrace(self.tracer.trace_order_seq(),
                                                             self.from_fsm.fsm_id if self.from_fsm else None,
                                                             self.to_fsm.fsm_id if self.to_fsm else None,
                                                             item.name))
        self.queue.put(item)

    def get(self, block=True, timeout=None):
        return self.queue.get(block, timeout)

    receive = get


def Channel(from_fsm, to_fsm, tracer, queue=None):
    if settings.instrumented:
        return _Channel(from_fsm, to_fsm, tracer, queue)
    if queue is not None:
        return queue
    else:
        return Queue()


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

    def __init__(self, context, name, fsm_id, states, initial_state, tracer, channel_tracer):
        self.context = context
        self.name = name
        self.fsm_id = fsm_id
        self.tracer = tracer
        self.channel_tracer = channel_tracer
        self.state = initial_state
        self.states = states
        self.inbox = Queue()
        self.thread = gevent.spawn(self.receive_messages)
        self.state.exec_handler('enter', self)

    def change_state(self, state, handling_message_type):
        if self.state:
            self.state.exec_handler('exit', self)
        if settings.instrumented:
            self.tracer.send_trace_message(messages.FSMTrace(self.tracer.trace_order_seq(),
                                                             self.name,
                                                             self.fsm_id,
                                                             self.state.name,
                                                             state.name,
                                                             handling_message_type))
        self.state = state
        if self.state:
            self.state.exec_handler('enter', self)

    def handle_message(self, message_type, message):
        self.state.exec_handler(message_type, self)

    def receive_messages(self):

        while True:
            gevent.sleep(1)
            message = self.inbox.get()
            message_type = message.name
            if message_type == 'Shutdown':
                break
            elif message_type == 'ChangeState':
                self.change_state(self.states[message.args['next_state']],
                                  message.args['handling_message_type'])
            else:
                self.handle_message(message_type, message)


FSM_TASKS = ['change_state', 'shutdown']


class State(object):

    def __init__(self, name, handlers):
        self.name = name
        self.handlers = handlers

    def exec_handler(self, msg_type, controller):
        if msg_type in self.handlers:
            print("{0} running {1}".format(self.name, msg_type))
            for task in self.handlers[msg_type]:
                print(task)
                for cmd in FSM_TASKS:
                    if cmd in task:
                        special_handler = getattr(self, 'handle_' + cmd)
                        special_handler(controller, task, msg_type)

    def handle_change_state(self, controller, task, msg_type):
        controller.inbox.put(messages.Event(controller.fsm_id,
                                            controller.fsm_id,
                                            'ChangeState',
                                            dict(next_state=task['change_state'],
                                                 handling_message_type=msg_type)))

    def handle_shutdown(self, controller, task, msg_type):
        controller.inbox.put(messages.Event(controller.fsm_id,
                                            controller.fsm_id,
                                            'Shutdown',
                                            dict(handling_message_type=msg_type)))


class _NullTracer(object):

    def trace_order_seq(self):
        return 0

    def send_trace_message(self, message):
        pass


NullTracer = _NullTracer()
