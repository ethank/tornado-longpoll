# Long Poll Framework
Version 0.1

This is a Tornado application which provides a good basis on which to build a long polling framework.

The framework has a submit and update handler. Submit is for pushing anything to the clients hanging on the update. In the Javascript, the update handler feeds the client, which then relatches on to the update.
