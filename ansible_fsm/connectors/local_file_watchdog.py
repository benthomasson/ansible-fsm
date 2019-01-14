
from watchdog.observers import Observer

import os
import gevent
from .. import messages
from itertools import count


class WatchDogEventChannel(object):

    def __init__(self, fsm_registry, configuration):
        self.fsm_registry = fsm_registry
        self.path = os.path.abspath(configuration.get('path', '.'))
        self.fsm_name = configuration.get('receiving_fsm', 'FSM1')
        self.watch_thread = gevent.spawn(self.watch_files)
        self.message_id_seq = count()

    def dispatch(self, event):
        event_type = type(event).__name__
        print(event_type)
        src_path = os.path.join(self.path, event.src_path)
        print(src_path)
        if self.fsm_name in self.fsm_registry:
            self.fsm_registry[self.fsm_name].inbox.put((1,
                                                        next(self.message_id_seq),
                                                        messages.Event(None,
                                                                          self.fsm_registry[self.fsm_name].fsm_id,
                                                                          event_type,
                                                                          {'src_path': src_path})))

    def watch_files(self):
        observer = Observer()
        observer.schedule(self, self.path, recursive=True)
        observer.start()
