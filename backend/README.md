BiddieServer
============

To update and rerun the server, just do the following:
git push heroku master

To test locally, run:
sudo mongod &
python main_server.py

To clone the repo use:
heroku git:clone -a nader-app

To test that the server is running do this in a browser (should see some text):
http://nader-app.herokuapp.com/


The server for the Biddie dating app. It provides a REST interface for doing various
things, such as adding users and getting matches.
