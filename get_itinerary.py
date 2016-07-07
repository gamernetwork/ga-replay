import argparse
from datetime import datetime

from ga_replay.replay import get_itinerary

parser = argparse.ArgumentParser(description='Get an itinerary of traffic called for a set of Google Analytics properties, between a given date range')
parser.add_argument('sites', type=str,
                    help='Comma delimited list of sitenames to get itineraries for (must be in config.GA_SITES)')
parser.add_argument('start', type=str,
                    help='The start date in format DD-MM-YYYY')
parser.add_argument('end', type=str,
                    help='The end date in format DD-MM-YYYY')
parser.add_argument('--extra-dimensions', type=str, default=[],
                    help="Comma delimited list of additional GA dimensions")
parser.add_argument('--outfile', type=str, default=None,
                    help="File to write the inventory to")
args = parser.parse_args()

def get_date(date_arg):
    return datetime.strptime(date_arg, "%d-%m-%Y").date()

sites = args.sites.split(',')
start = get_date(args.start)
end = get_date(args.end)
extra_dimensions = args.extra_dimensions.split(',')

get_itinerary(start=start, end=end, 
    sites=sites, 
    extra_dimensions=extra_dimensions,
    outfile_path=args.outfile)
