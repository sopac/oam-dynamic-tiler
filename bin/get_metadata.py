#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function

import json
import math
import os
import re
import sys

import arrow
import click
import rasterio
from rasterio.warp import transform_bounds

from get_zoom import get_zoom, get_zoom_offset


@click.command(context_settings={
    'ignore_unknown_options': True,
})
@click.option("--include-mask", is_flag=True, help="Include a mask URL")
@click.option("-t", "--title", help="Source title")
@click.option("-a", "--acquisition-start", help="Acquisition start date")
@click.option("-A", "--acquisition-end", help="Acquisition end date")
@click.option("-p", "--provider", help="Provider / owner")
@click.option("-P", "--platform", help="Imagery platform")
@click.option("-U", "--uploaded-at", help="Uploaded at")
@click.argument("_", nargs=-1, type=click.UNPROCESSED)
@click.argument("prefix")
def get_metadata(
    include_mask,
    title,
    acquisition_start,
    acquisition_end,
    provider,
    platform,
    uploaded_at,
    prefix,
    _,
):
    scene = "{}.tif".format(prefix)
    scene_vrt = "{}_warped.vrt".format(prefix)
    mask_vrt = "{}_warped_mask.vrt".format(prefix)
    footprint = "{}_footprint.json".format(prefix)

    with rasterio.Env():
        input = re.sub("s3://([^/]+)/", "http://\\1.s3.amazonaws.com/", scene)
        try:
            with rasterio.open(input) as src:
                bounds = transform_bounds(src.crs, {'init': 'epsg:4326'}, *src.bounds)
                approximate_zoom = get_zoom(scene)
                maxzoom = approximate_zoom + 3
                minzoom = max(approximate_zoom - get_zoom_offset(src.width, src.height, approximate_zoom), 0)
                source = re.sub("s3://([^/]+)/", "http://\\1.s3.amazonaws.com/", scene_vrt)
                mask = re.sub("s3://([^/]+)/", "http://\\1.s3.amazonaws.com/", mask_vrt)
                footprint = re.sub("s3://([^/]+)/", "http://\\1.s3.amazonaws.com/", footprint)

                meta = {
                  "bounds": bounds,
                  "center": [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, (minzoom + approximate_zoom) / 2],
                  "maxzoom": maxzoom,
                  "meta": {
                    "approximateZoom": approximate_zoom,
                    "footprint": footprint,
                    "height": src.height,
                    "source": source,
                    "width": src.width,
                  },
                  "minzoom": minzoom,
                  "name": title or source,
                  "tilejson": "2.1.0"
                }

                if include_mask:
                    meta["meta"]["mask"] = mask

                if acquisition_start:
                    meta["meta"]["acquisitionStart"] = arrow.get(acquisition_start).for_json()

                if acquisition_end:
                    meta["meta"]["acquisitionEnd"] = arrow.get(acquisition_end).for_json()

                if platform:
                    meta["meta"]["platform"] = platform

                if provider:
                    meta["meta"]["provider"] = provider

                if uploaded_at:
                    meta["meta"]["uploadedAt"] = arrow.get(uploaded_at).for_json()

                print(json.dumps(meta))
        except (IOError, rasterio._err.CPLE_HttpResponseError) as e:
            print("Unable to open '{}': {}".format(input, e), file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    get_metadata()
