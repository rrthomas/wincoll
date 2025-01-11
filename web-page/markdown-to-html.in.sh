#!/bin/sh
# Convert given Markdown file to HTML fragment on stdout
markdown -f footnote,nopants,noalphalist,nostyle,fencedcode "$@"
