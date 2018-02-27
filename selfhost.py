#!/usr/bin/env python3
'''Self hosted Artsy.'''

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from artsy import generate_static_site
import utils

# Configure
args = utils.parse_args()

# Generate
print("Generating content...")
limit = utils.get_limit_from_args(args)
generate_static_site(args.indir, args.outdir, limit=limit, force=args.force)

# Host
print("Hosting content on http://localhost:8000/")
os.chdir(os.path.join(os.path.dirname(__file__), args.outdir))

server_address = ('', 8000)
httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
httpd.serve_forever()
