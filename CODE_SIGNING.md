# Code signing policy

## Status

We intend to apply to SignPath Foundation. Acceptance and signing are **not yet granted**. Current artifacts are unsigned; do not disable Smart App Control or any security protection to run them. This policy is not an endorsement by SignPath.

If accepted, attribution will state: “Free code signing provided by SignPath.io, certificate by SignPath Foundation.” That statement will apply only after the service is granted and the specific artifact is signed.

## Roles and controls

- Author, reviewer and release/signing approver: [lostincat](https://github.com/lostincat).
- Only this repository's own source and build outputs may be submitted for signing.
- Each signing request requires explicit maintainer approval; never sign arbitrary user uploads, trading strategies, vendor binaries or dependencies under this project's identity.
- Contributors and maintainers must use MFA for repository and signing-service access before enrolling in signing. Enrollment checks are pending.
- GitHub Actions builds and tests the source on Windows. Build artifacts are unsigned. Signing integration and artifact provenance verification will be configured with SignPath after acceptance.

## Privacy policy

The program does not transmit information to other networked systems. It processes caller-supplied code and desktop compiler output locally. Runtime evidence may contain private source code and must never be uploaded to this repository or the signing service. See [SECURITY.md](SECURITY.md).

The public GitHub repository and any future signing service process repository/build data under their own service policies. No local XQ source files, credentials or runtime logs are part of a signing submission.
