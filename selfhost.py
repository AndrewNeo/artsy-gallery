#!/usr/bin/env python3
'''Self hosted Artsy.'''

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from artsy import generate_static_site

# Configure
# TODO: Move this to command line arguments
indir = "testdata"
outdir = "output"
limit = "*"

# Generate
print("Generating content...")
generate_static_site(indir, outdir, limit)

# Host
print("Hosting content on http://localhost:8000/")
os.chdir(os.path.join(os.path.dirname(__file__), outdir))

server_address = ('', 8000)
httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
httpd.serve_forever()
