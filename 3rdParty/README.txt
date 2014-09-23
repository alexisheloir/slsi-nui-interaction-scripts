
Third party libraries:

- websocket [https://pypi.python.org/pypi/websocket-client/]
It is needed when the Leap Motion receiver is used to directly connect to the websocket, instead of using the LeapForwarder (This is a flag in the source).
If needed, must be copied manually into the Blender-embedded python installation:
Select the Blender app and right click "Show Package Contents" 
-> Contents/MacOS/2.xx/python/lib/python3.3/

- six [https://pypi.python.org/pypi/six]
A python v2/v3 compatibility framework. Needed by websocket.

