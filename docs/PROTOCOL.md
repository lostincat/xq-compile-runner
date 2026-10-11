# Local job protocol

Native CLI: `XqCompileRunner.exe health` or `XqCompileRunner.exe run CONFIG INPUT OUTPUT`.
The health command reports program identity only; it does not validate XQ readiness.

Request has exactly four properties:

```json
{"target":"OSS_CompileProbe","code":"<caller-provided source>","sha256":"<lowercase hex>","timeout_seconds":40}
```

Hash is SHA-256 of UTF-8 source after CRLF to LF conversion and trimming surrounding whitespace. Source must be nonblank, have no NUL, and be at most 20,000 UTF-16 code units. Timeout is an integer from 1 to 45. Native and Python Unicode trimming should be verified for unusual whitespace; a disagreement stops the job.

Output `ok` means desktop operation and evidence capture succeeded, **not** successful compilation. `compile_passed`, `error_count`, `warning_count`, `summary`, `errors`, `source_readback`, `compile_epoch`, and `trace` describe the result. Failure has `ok:false`, `error`, `stage`, `trace`. The Python wrapper returns FAIL for compile errors, nonzero exit status, missing evidence, wrong source or timeout.

The caller chooses local file locations; the model must never control the executable/config path or arbitrary commands. Native output parent must already exist. The Python wrapper creates a new evidence directory and refuses reuse. No automatic repair, resubmission, order execution or network API is included.
