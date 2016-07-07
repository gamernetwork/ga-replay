GA Replay
=========

Replay historic traffic to your website(s), for the purposes of load testing or
platform building!

GA Replay provides a mechanism for querying Google Analytics for a site's pageviews
over a defined period of time.  The pageviews are saved locally as a traffic
itinerary which can then be replayed against a site through a simulator script.

Install
-------

Python3+ only, sorry!

- `pip install -r requirements.txt`
- Copy `config.py-example` to `config.py` and override settings as appropriate.

Generating service account
--------------------------

  - Register for Google Developers Console: https://console.developers.google.com/
  - Create a project
  - Go to APIs & Auth -> Credentials
  - Click 'Create a new client ID'
    - Choose 'Service account'
  - You will be prompted to save a .p12 file - this is the private key file referenced in GA/config.py
  - Copy the service account email address and pop into GA/config.py

Usage
-----

To get a traffic itinerary:

`python get_itinerary eurogamer.net 04-07-2016 04-07-2016 --extra-dimensions=ga:fullReferrer`

To replay a traffic itinerary:

`python run_replay.py itineraries/itinerary.csv simple --start 1700`

Note: The above will replay production traffic against a production website!


Extensions
----------

It's possible to customise the request logic used by the simulator.  To do this,
a custom `request_function` needs to be added to the `ga_replay.replay.REQUEST_FUNCTIONS`
dictionary.  The custom request function is called for every pageview in the itinerary.

As an example, the `analytics_request` function was written for the purposes of
calling through to a proprietary analytics server.  A custom request function could
be used to call through to a staging domain rather than production.


GOTCHAS
-------

- The Google Analytics API does not provide a `ga:seconds` dimension.  This means
  that the highest resolution of data that can be acted on is per-minute. 
  So the simulator attempts to even out requests across a minute by dividing the
  minute in to `config.REQUEST_BUCKETS` buckets (6 10-second buckets, by default).
  The result is that simulated traffic is likely to spike around the start of
  each request bucket and real spikes that happened on a site between minutes are
  difficult to model.
