#!/usr/bin/env python3
"""Compose the current assembly viewer from exact R13 exports."""
import cad
builder=cad.load('build_preview',cad.base.HERE)
builder.cad=cad
if __name__=='__main__':builder.build()
