
Simple Dashboard Example
------------------------

In one terminal run ansible-fsm:

    ansible-fsm run tests/inputs/single_with_external_events.yml  --connectors tests/inputs/connectors_websocket.yml

In another terminal run a webserver from this directory:

    python -m http.server


In another terminal run tail the log file:

    tail -f fsm.log

Navigate to http://localhost:8000

Press the Event1 button and then Event2 button. Repeat. Watch the log
file and the output of ansible-fsm.

Enjoy building custom dashboards with your Ansible Automata.

