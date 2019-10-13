[![travis ci status](https://travis-ci.org/hymnis/dead-drop-python.svg?branch=master)](https://travis-ci.org/hymnis/dead-drop-python)

# dead-drop - now with more python

Live at [dead-drop.me](https://dead-drop.me)

Secure text sender, generates a one-time link and password. stores encrypted in MongoDB.

The intention here is to be self contained, and operate all in browser to minimize attack vectors.


## Development Instructions

1. install mongodb
2. install python3
3. install/activate virtualenv
4. pip install -r requirements/dev.txt
5. python wsgi.py


## License

This code is free to use as per the license, it would be polite to put a link to dead-drop.me in the footer however.


## Using with nginx

For prod ([dead-drop.me](https://dead-drop.me)), I'm using UWSGI instructions from here:
https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04
