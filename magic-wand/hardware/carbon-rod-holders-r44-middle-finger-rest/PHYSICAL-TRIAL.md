# R44 physical trial — rejected, 15 November 2026

The single-carrier job completed all 209 layers. The final camera image showed
the key carrier and its timelapse tower still standing. Both heater targets
were off. This establishes machine-cycle completion, not a usable assembly.

The physical result was rejected: material occupied the switch openings and
other spaces that should accept the electronics. A photograph of the removed
part was inspected. Keep the delivered CAD and print files unchanged as evidence;
do not reprint this recipe as a corrected candidate.

## Exact delivered file

- Archive: `exports/key-holder-only/R44-Key-Holder-Only-print-only.3mf`
- Archive SHA-256: `92aa2fbb89d0bd3de18292a2c7c4d28cf0c7234ebfedf4372b8d9ccf97141fa2`
- Executable G-code SHA-256: `29470145a5ce54e843cb19e870f31418c25c2201d256d801fcc074a9cea5b7e1`
- The retained reopened archive's G-code is byte-identical to the delivered file.

## Established preparation and acceptance failure

The carrier has object-level automatic normal support enabled, with `snug`
style, a 0.2 mm top gap, two top-interface layers and 0.2 mm interface spacing.
Those object settings override the disabled global support setting. The actual
executable file includes support, support interface and support-transition paths
inside every outer switch volume (`key_0_switch`, `key_2_switch`,
`key_3_switch`, `key_4_switch`). The existing `slice-audit.json` recorded these
spaces as requiring support removal, with physical cleanup unverified.

The earlier pass tested permanent-material clearance separately and accepted
temporary support using a small-fragment removal route. That did not establish
that the dense support could practically be removed from this delicate part.
An opening containing temporary support is still obstructed before cleanup.

The next candidate must account for all deposited material in working spaces,
including support and interface. Keep the existing strength and unsupported-start
checks: turning support off alone is not a manufacturing solution. Prefer an
orientation or local geometry that leaves the required openings usable, and
demonstrate access and separation wherever support remains necessary.

The physical photograph does not measure bonding, removal force, fit, strength
or comfort. The deterministic support placement is established from the file;
the extent of fusion and any additional physical defects remain unmeasured.
