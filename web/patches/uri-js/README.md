# Local uri-js remediation for CVE-2026-93690

There is no published fixed uri-js release. This is a local adaptation of
[upstream PR #107](https://github.com/garycourt/uri-js/pull/107), not an
upstream version bump. The installed package versions remain 4.2.2 and 4.4.1.
Reviewed PR head: `d5cff68221e7372ba2176b6dd3a1370cb5130140`.
The upstream BSD license is reproduced in LICENSE and remains in each package.

The reviewed change consumes all characters, including U+2028/U+2029, with
`[\s\S]`, rejects empty segment matches, and checks that every iteration
shrinks the input. The algorithm otherwise retains uri-js dot-segment behavior.
The adaptation uses a self-contained function in all three shipped JavaScript
distributions, including the minified entry point. Original surrounding code
and license notices are preserved; stale sourceMappingURL directives are
removed because the original maps no longer describe the patched function.

Root npm and web npm/pnpm postinstall hooks apply the patch without fetching
code or adding dependencies. Container builds copy this directory before
installing, including the downstream npm build that excludes web/.npmrc.
The walker follows nested and pnpm-linked installations, deduplicates real
paths, and checks every uri-js copy it finds. SHA-256 hashes in hashes.json
identify the reviewed original and patched distributions from the published
4.2.2 and 4.4.1 packages. Unknown versions or contents fail installation rather
than silently skipping remediation. Reapplying the patch is safe. Files are
replaced rather than overwritten to avoid modifying pnpm store hardlinks.

Do not use `--ignore-scripts` for a real install without explicitly running
`npm run postinstall` afterward. Dependency tools and scanners may still report
the original package versions; this patch does not claim an upstream release
or suppress CVE findings. Remove it when a verified fixed release can replace
all affected dependency chains, regenerating the locks and running regressions.

Run `npm run test:uri-js` in both root and web after installation. Tests require
every installed distribution to have its reviewed patched hash before testing
idempotence. Each distribution runs its Unicode and normal dot-segment cases
in a separate child with a two-second timeout and a bounded heap, so the
original infinite loop cannot hang the test runner. CommonJS and minified
distributions also exercise serialize/resolve with IRI support. The ES module's
patched function is exercised in isolation without changing module resolution.

Validation must cover root `npm clean-install`, web `pnpm@10 install
--frozen-lockfile`, and an independent downstream-style web `npm clean-install
--legacy-peer-deps` without .npmrc. Run the regression command after each;
then run the production builds, plugin build, coverage, lockfile checks and
applicable pre-commit checks according to the repository CI conventions.
