#!/bin/sh

# Execute Gunicorn command
gunicorn -w 1 -b 0.0.0.0:80 app:app
