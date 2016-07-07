import csv, time, requests, os
from datetime import datetime, timedelta
from collections import OrderedDict

import asyncio
from aiohttp import ClientSession

from ga_replay.analytics import analytics
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

try:
    REQUEST_BUCKETS = config.REQUEST_BUCKETS
except AttributeError:
    REQUEST_BUCKETS = 6

def _write_itinerary(itinerary, outfile_path):
    """
    Write itinerary to CSV file.
    """
    with open(outfile_path, "wt") as f:
        writer = csv.writer(f)
        writer.writerows(itinerary)
    
def get_itinerary(start, end, sites, outfile_path=None, extra_dimensions=[]):
    """
    Generate a requests itinerary CSV, given a start date, end date, file path
    and extra dimensions.  The itinerary is generated by grabbing the requests
    logged in historical google analytics data between the dates provided.

    This will generate a CSV of format:
        `HOUR,MINUTE,SITE_DOMAIN,PATH,[extra_dimensions],PAGEVIEWS`

    Args:
        * `start` - `date` - the date for the itinerary to begin
        * `end` - `date` - the date for the itinerary to end
        * `sites` - `iterable` - iterable of site domain strings
        * `outfile_path` - `string` - file path of the CSV to write to
        * `extra_dimensions` - `iterable` - iterable of additional GA dimensions
            to request
    """
    if not outfile_path:
        outfile_path = os.path.join(PROJECT_ROOT, "itineraries", "itinerary.csv")
    site_itineraries = {}
    for site in sites:
        ga_id = config.GA_SITES[site]
        print("**** Grabbing itinerary for %s ****" % site)
        site_itinerary = analytics.get_itinerary(start=start, end=end, 
            ga_id=ga_id, extra_dimensions=extra_dimensions)
        site_itineraries[site] = site_itinerary
        print("**** DONE ****")
    print("**** Flattening site itineraries ****")
    flat_itinerary = []
    for site, itinerary in site_itineraries.items():
        for row in itinerary:
            # Transpose to format:
            # [hour, minute, site, path, extra_dimensions*, pageviews] 
            flat_row = [row[1], row[2], site, row[0], ]
            flat_row.extend(row[3:])
            flat_itinerary.append(flat_row)
    print("**** DONE ****")
    print("**** Sorting itinerary by request time ****")
    flat_itinerary.sort(key=lambda row: row[0] + row[1] + row[3])
    print("**** DONE ****")
    print("**** Writing final itinerary ****")
    _write_itinerary(flat_itinerary, outfile_path)
    print("**** DONE ****")

async def dummy_request(domain, path, extra_dimensions=[]):
    print("Requesting %s %s %s" % (domain, path, extra_dimensions))

async def simple_request(domain, path, extra_dimensions):
    url = "http://%s%s" % (domain, path)
    async with ClientSession() as session:
        async with session.get(url) as response:
            response = await response.read()

async def analytics_request(domain, path, extra_dimensions=[]):
    analytics_host = config.ANALYTICS_HOST
    data = {'path': path, 'site': domain, 'referrer': extra_dimensions[0]}
    url = "http://%s/record_pageview/" % analytics_host
    async with ClientSession() as session:
        async with session.post(url, data=data) as response:
            response = await response.read()

REQUEST_FUNCTIONS = {
    "dummy": dummy_request,
    "simple": simple_request,
    "analytics": analytics_request,
}

def _load_itinerary(itinerary_path):
    flat_itinerary = []
    with open(itinerary_path, "rt") as f:
        reader = csv.reader(f)
        flat_itinerary = list(reader)
    itinerary = OrderedDict({})
    for row in flat_itinerary:
        key = int(row[0] + row[1])
        try:
            itinerary[key].append(row)
        except KeyError:
            itinerary[key] = [row]
    return itinerary

def buckets(items, bucket_count):
    """
    Split a list in to (roughly) evenly sized buckets.

    Args:
        * `items` - `list` - the items to split in to buckets
        * `bucket_count` - `int` - the number of buckets to split in to

    Returns:
        A list of `bucket_count` buckets
    """
    bucket_size = len(items) / float(bucket_count)
    return [ items[int(round(bucket_size * i)): int(round(bucket_size * (i + 1)))] for i in range(bucket_count) ]

loop = asyncio.get_event_loop()

def simulate_from_itinerary(itinerary_path, request_func=dummy_request, start_time=None):
    """
    Run the network requests in a given itinerary to replay traffic.

    Args:
        * `itinerary_path` - `string` - the path to the itinerary CSV file to replay
        * `[request_func]` - `function` - the function to use when making a request
        * `[start_time]` - `string` - string of format "HHMM" to indicate 
            what timestamp to start replaying the itinerary from
    """
    itinerary = _load_itinerary(itinerary_path)
    all_itinerary_timestamps = list(itinerary.keys())
    if start_time:
        start_time = int(start_time)
        first_timestamp_index = all_itinerary_timestamps.index(start_time)
        all_itinerary_timestamps = all_itinerary_timestamps[first_timestamp_index:]

    timestamp = all_itinerary_timestamps.pop(0)
    next_run = datetime.now()
    start = datetime.now()
    start_timestamp = timestamp
    print("**** Replaying traffic... ****")
    while True:
        minute_start = datetime.now()
        if datetime.now() < next_run:
            # It's not time to run the next timestamp in the itinerary yet, so hold off
            time.sleep(1)
            continue
        requests = itinerary[timestamp]
        request_buckets = buckets(requests, REQUEST_BUCKETS)
        for bucket_count, request_bucket in enumerate(request_buckets, 1):
            next_bucket_start = minute_start + (timedelta(seconds=60/REQUEST_BUCKETS) * bucket_count)
            request_tasks = []
            for request in request_bucket:
                pageviews = int(request[-1])
                # For each request in the itinerary, simulate the number of requests
                #   logged by `pageviews`
                for i in range(0, pageviews):
                    task = asyncio.ensure_future(
                        request_func(domain=request[2], path=request[3], extra_dimensions=request[4:-1])
                    )
                    request_tasks.append(task)
            loop.run_until_complete(asyncio.wait(request_tasks))
            # Wait until it's time to move on to the next request bucket
            while True:
                if datetime.now() < next_bucket_start and bucket_count < REQUEST_BUCKETS:
                    time.sleep(1)
                    continue
                else:
                    break
        # What's the next timestamp we need to move on to?
        try:
            next_timestamp = all_itinerary_timestamps.pop(0)
        except IndexError:
            break
        # When should we start running the itinerary for the next timestamp?
        timestamp = next_timestamp
        total_minutes_passed = timestamp - start_timestamp
        next_run = start + (timedelta(minutes=1) * total_minutes_passed)
    print("**** Done! ****")
