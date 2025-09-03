# Polling App

Polling App is a FastApi web application that allows users to create and vote on polls. Users can create a poll with multiple choices and other users can vote on the poll. The app also provides websocket api to subscribe to live updates of the polls.

## Features

- Create a poll with multiple choices
- Vote on a poll
- Live updates to the users about the current state of the poll
- Database integration

## Installation

To install the app, create a virtual env and run the following command:

```
pip install poetry
poetry install
```

## Development

To run the development version of the app, run the following command:

```
./run.sh
```

## Testing

To run the tests, run the following command:

```
./test.sh
```

 Mock frontend for testing can be found at `./frontend`