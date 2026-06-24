# Security policy

## Supported versions

Security fixes are handled on the latest released minor version. Before 2.0.0,
that means the `1.x` line.

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| < 1.0 | No |

## Reporting a vulnerability

Please do not open a public issue for vulnerabilities. Use GitHub private
vulnerability reporting when available, or contact the maintainers directly.

Include:

- affected version or commit;
- minimal reproduction;
- impact assessment;
- whether optional integrations such as Pythia, HepMC3, MadGraph, Docker or Dash
  are involved.

## Scope

SET-ANUBIS wraps external scientific software. Vulnerabilities in Pythia8,
HepMC3, MadGraph, MARTY, Docker or system packages should also be reported to the
corresponding upstream projects.
