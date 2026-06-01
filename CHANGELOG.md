# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.4](https://github.com/atriumn/noxaudit/compare/v1.2.3...v1.2.4) (2026-05-30)


### Bug Fixes

* **benchmark:** drop invalid focus token and phantom model IDs in corpus.yml ([#162](https://github.com/atriumn/noxaudit/issues/162)) ([ec85982](https://github.com/atriumn/noxaudit/commit/ec859823546e97b2e449a87301d77385344f3f90))
* remove dead webhook field from NotificationConfig ([#161](https://github.com/atriumn/noxaudit/issues/161)) ([c77b0af](https://github.com/atriumn/noxaudit/commit/c77b0af767bd14f22674e125bcbff229a9f916df)), closes [#158](https://github.com/atriumn/noxaudit/issues/158)
* route pre-pass to gpt-5-mini to avoid long-context SKU ([#151](https://github.com/atriumn/noxaudit/issues/151)) ([2de80de](https://github.com/atriumn/noxaudit/commit/2de80deabb794d8aa1d96ca4b75b666f409945c3))


### Miscellaneous

* add arqo issue templates ([#156](https://github.com/atriumn/noxaudit/issues/156)) ([c2ae679](https://github.com/atriumn/noxaudit/commit/c2ae679b9715c50e263196b6e4280ad5207d483e))
* **deps:** bump amondnet/vercel-action from 25 to 42 ([#155](https://github.com/atriumn/noxaudit/issues/155)) ([f4cb63d](https://github.com/atriumn/noxaudit/commit/f4cb63d45eef2d92ef301167a2ab193a9691db81))
* remove npm dependabot entry — no package.json in this repo ([#153](https://github.com/atriumn/noxaudit/issues/153)) ([dd2d069](https://github.com/atriumn/noxaudit/commit/dd2d0691ed0da9976c166e89d34af4c72228b71f))
* stop committing drafts/; remove orphaned retrieve_chunked.py ([#160](https://github.com/atriumn/noxaudit/issues/160)) ([05743b8](https://github.com/atriumn/noxaudit/commit/05743b88fe60d35d171fa7ebd04677870386727c)), closes [#157](https://github.com/atriumn/noxaudit/issues/157)

## [1.2.3](https://github.com/atriumn/noxaudit/compare/v1.2.2...v1.2.3) (2026-03-27)


### Bug Fixes

* increase max_completion_tokens from 4096 to 16384 ([#148](https://github.com/atriumn/noxaudit/issues/148)) ([a45ef92](https://github.com/atriumn/noxaudit/commit/a45ef9276cf63bdeaa8630c6fc22a50b6f8afe10))

## [1.2.2](https://github.com/atriumn/noxaudit/compare/v1.2.1...v1.2.2) (2026-03-24)


### Bug Fixes

* reduce pre-pass chunk headroom from 75% to 50% ([#144](https://github.com/atriumn/noxaudit/issues/144)) ([9e6439d](https://github.com/atriumn/noxaudit/commit/9e6439d7c18fa10da1cf9cc2b635e474bb48bfc7))

## [1.2.1](https://github.com/atriumn/noxaudit/compare/v1.2.0...v1.2.1) (2026-03-24)


### Bug Fixes

* chunk pre-pass sync calls to fit model context window ([#141](https://github.com/atriumn/noxaudit/issues/141)) ([1551dc5](https://github.com/atriumn/noxaudit/commit/1551dc5b3ca6071534e6f3540223df5f1b36d0d9))

## [1.2.0](https://github.com/atriumn/noxaudit/compare/v1.1.10...v1.2.0) (2026-03-24)


### Features

* use sync API for pre-pass instead of batch API ([#139](https://github.com/atriumn/noxaudit/issues/139)) ([d6c4b4e](https://github.com/atriumn/noxaudit/commit/d6c4b4e204ef88aa764a2b236cb7e05515bff51b))

## [1.1.10](https://github.com/atriumn/noxaudit/compare/v1.1.9...v1.1.10) (2026-03-24)


### Bug Fixes

* auto-enable pre-pass when tokens exceed model context window ([#137](https://github.com/atriumn/noxaudit/issues/137)) ([8e30e57](https://github.com/atriumn/noxaudit/commit/8e30e5758f9222bb8c2424582e072ccac03ab85a))

## [1.1.9](https://github.com/atriumn/noxaudit/compare/v1.1.8...v1.1.9) (2026-03-24)


### Bug Fixes

* add retrieve_batch to BaseProvider interface ([#135](https://github.com/atriumn/noxaudit/issues/135)) ([b12d7fe](https://github.com/atriumn/noxaudit/commit/b12d7fe88df2e872be37d53b07526da8d0eea099))

## [1.1.8](https://github.com/atriumn/noxaudit/compare/v1.1.7...v1.1.8) (2026-03-22)


### Bug Fixes

* add Dart support to all focus areas ([#133](https://github.com/atriumn/noxaudit/issues/133)) ([3068361](https://github.com/atriumn/noxaudit/commit/3068361e9cee4974a01629eb1571e23afa8b5d0f))


### Miscellaneous

* update uv.lock for 1.1.7 ([c87a1c8](https://github.com/atriumn/noxaudit/commit/c87a1c8ca3c3729c7eeb4995147ec7c79f2bb04e))

## [1.1.7](https://github.com/atriumn/noxaudit/compare/v1.1.6...v1.1.7) (2026-03-21)


### Bug Fixes

* inject synthetic finding when repo has no test files ([17cdd99](https://github.com/atriumn/noxaudit/commit/17cdd99b88d0e5a0e1ba8f6647b3f53ad17e87e3))

## [1.1.6](https://github.com/atriumn/noxaudit/compare/v1.1.5...v1.1.6) (2026-03-20)


### Bug Fixes

* update send-email workflow for per-audience draft files ([5a23681](https://github.com/atriumn/noxaudit/commit/5a23681422e4533cab5621cd1be7f78683e98755))


### Documentation

* set up Fumadocs to replace MkDocs Material ([#128](https://github.com/atriumn/noxaudit/issues/128)) ([b6dc3e7](https://github.com/atriumn/noxaudit/commit/b6dc3e74987025204021f385cbc77ea8d54a8c93))

## [1.1.5](https://github.com/atriumn/noxaudit/compare/v1.1.4...v1.1.5) (2026-03-19)


### Bug Fixes

* add cryyer product config for release email drafts ([f8c03ca](https://github.com/atriumn/noxaudit/commit/f8c03ca02fd143bf9b5eabe6d73801f6a8046287))
* keep drafts/ gitignored, use git add -f in workflow ([1f397b0](https://github.com/atriumn/noxaudit/commit/1f397b0db7443e43ffa9c9fc462ac81d918a870a))
* stop ignoring drafts/ so cryyer can commit email drafts ([e73d8bd](https://github.com/atriumn/noxaudit/commit/e73d8bd28f7670a956de54601ee94cc7954bc009))
* update draft email workflow to handle multiple audiences ([942e3d7](https://github.com/atriumn/noxaudit/commit/942e3d74e14a70c8ec017c5f043d7e5438c2ac1b))


### Miscellaneous

* sync release-please manifest to v1.1.4 ([740132a](https://github.com/atriumn/noxaudit/commit/740132a6c89225ddaf718e5d0553c8dce2d96e85))

## [1.1.3](https://github.com/atriumn/noxaudit/compare/v1.1.2...v1.1.3) (2026-03-08)


### Bug Fixes

* remove "daily" assumptions from pricing.py output ([#109](https://github.com/atriumn/noxaudit/issues/109)) ([e246fee](https://github.com/atriumn/noxaudit/commit/e246feefcc0ce70819aa5eeea108660cbe03ed1b))

## [1.1.2](https://github.com/atriumn/noxaudit/compare/v1.1.1...v1.1.2) (2026-03-07)


### Bug Fixes

* remove "nightly" branding from tagline and core messaging ([#106](https://github.com/atriumn/noxaudit/issues/106)) ([44e1aef](https://github.com/atriumn/noxaudit/commit/44e1aefdfbb8e38e225ae5bde8828a86f1ff6038))


### Documentation

* reframe scheduling as optional, not the default path ([#108](https://github.com/atriumn/noxaudit/issues/108)) ([469bfa7](https://github.com/atriumn/noxaudit/commit/469bfa7353df9b69f51a02efe965ccc9e831ed5a))

## [1.1.1](https://github.com/atriumn/noxaudit/compare/v1.1.0...v1.1.1) (2026-03-07)


### Miscellaneous

* remove ralph dev artifacts and improve gitignore ([8efbbd6](https://github.com/atriumn/noxaudit/commit/8efbbd6965879a1c8ebc66aa92fd36acea6e6c93))


### Documentation

* add SECURITY.md, CODE_OF_CONDUCT.md, and issue templates ([c31bf08](https://github.com/atriumn/noxaudit/commit/c31bf08a6fec02ba46be70c5162dc8b719a45e1a))

## [1.1.0](https://github.com/atriumn/noxaudit/compare/v1.0.1...v1.1.0) (2026-03-07)


### Features

* add Next.js marketing site and migrate docs to subdomain ([fcb27bf](https://github.com/atriumn/noxaudit/commit/fcb27bf584411c95e0cc6f62749bed5f8e519788))


### Bug Fixes

* **test:** remove brittle version prefix assertion in SARIF test ([caf8ae3](https://github.com/atriumn/noxaudit/commit/caf8ae34217c812b05073178e6f4f4c318b60a91))

## [1.0.1](https://github.com/atriumn/noxaudit/compare/v1.0.0...v1.0.1) (2026-03-06)


### Documentation

* update model references and publish benchmark results ([#99](https://github.com/atriumn/noxaudit/issues/99)) ([438202b](https://github.com/atriumn/noxaudit/commit/438202bc2195c5f282dab9b0d8ed6b8c5216966f))

## [1.0.0](https://github.com/atriumn/noxaudit/compare/v0.1.0...v1.0.0) (2026-03-06)


### ⚠ BREAKING CHANGES

* `noxaudit run` (no --focus) now audits all 7 focus areas instead of using a day-of-week schedule. The `noxaudit schedule` command is removed. The `schedule` and `frames` config keys are deprecated (emit DeprecationWarning if present).

### Features

* add benchmark runner script and corpus definition ([#81](https://github.com/atriumn/noxaudit/issues/81)) ([3930b99](https://github.com/atriumn/noxaudit/commit/3930b994d8874aa8240e316e7c3e290a212e2e5d))
* add frame-based config and schedule system ([#30](https://github.com/atriumn/noxaudit/issues/30)) ([#40](https://github.com/atriumn/noxaudit/issues/40)) ([92cc7b1](https://github.com/atriumn/noxaudit/commit/92cc7b1451d4a402c76a4deb4c9389f09b8b7392))
* add Gemini 2.5 Pro, 3 Flash pricing and 50% batch discount ([793342d](https://github.com/atriumn/noxaudit/commit/793342dccd6849990d5a8713d14a8177d349d32d))
* add noxaudit baseline command to suppress existing findings on adoption ([#38](https://github.com/atriumn/noxaudit/issues/38)) ([5dcce18](https://github.com/atriumn/noxaudit/commit/5dcce1858a6abfba9ffdd73bd6da2f21259914b6))
* add noxaudit estimate command with pricing.py ([#37](https://github.com/atriumn/noxaudit/issues/37)) ([0a5a008](https://github.com/atriumn/noxaudit/commit/0a5a0086fe8433e4d66f9f7b5a23f1dd8559f7f1)), closes [#28](https://github.com/atriumn/noxaudit/issues/28)
* add OpenAI provider with GPT-5 family support ([#35](https://github.com/atriumn/noxaudit/issues/35)) ([#44](https://github.com/atriumn/noxaudit/issues/44)) ([ae77425](https://github.com/atriumn/noxaudit/commit/ae7742549a2e2887501fa7b239332bc8496c88fd))
* add patterns focus area ([fd9e68e](https://github.com/atriumn/noxaudit/commit/fd9e68e413c2164b9b830267f6b9f491b7219615))
* add SARIF 2.1.0 output format for GitHub Code Scanning ([#39](https://github.com/atriumn/noxaudit/issues/39)) ([c139aed](https://github.com/atriumn/noxaudit/commit/c139aed98ec0e60088bb0391db64ff155dfa32f7))
* add testing, hygiene, dependencies, performance focus areas ([3bd6c3d](https://github.com/atriumn/noxaudit/commit/3bd6c3d4f7090d079462cb5f9b2a3da9a7e985eb))
* batch API support with submit/retrieve split ([afa12cd](https://github.com/atriumn/noxaudit/commit/afa12cdc6aa3cb9485c77ec9f0e4c57396a2ba20))
* benchmark Phase 1 — 10 models × 2 repos quality baseline ([#90](https://github.com/atriumn/noxaudit/issues/90)) ([5937b78](https://github.com/atriumn/noxaudit/commit/5937b78df4a7bd0ef6abf09d16b2fa5cd565ee11))
* **benchmark:** add claude-sonnet-4-6, claude-opus-4-6, and openai models to corpus; replace gemini-2.0-flash with gemini-2.5-flash-lite; add gemini-3.1-pro-preview pricing ([#95](https://github.com/atriumn/noxaudit/issues/95)) ([a9eab32](https://github.com/atriumn/noxaudit/commit/a9eab3229c4b8ef31016040ef93920a2f137b28a))
* **benchmark:** add scorecard analysis script ([#96](https://github.com/atriumn/noxaudit/issues/96)) ([ab9404a](https://github.com/atriumn/noxaudit/commit/ab9404a09c941405ae19442be40fa34d89013432)), closes [#88](https://github.com/atriumn/noxaudit/issues/88)
* combined focus areas + test suite + CI ([c6116b0](https://github.com/atriumn/noxaudit/commit/c6116b075f025001725e55876005fd6972d8250c))
* implement Gemini Batch API in GeminiProvider (50% discount) ([#71](https://github.com/atriumn/noxaudit/issues/71)) ([df7d9be](https://github.com/atriumn/noxaudit/commit/df7d9beb44e1a7b0fc702d522e986d15381ca8ad))
* implement MCP server for AI coding tool integration ([#18](https://github.com/atriumn/noxaudit/issues/18)) ([71f2e46](https://github.com/atriumn/noxaudit/commit/71f2e4673e0e50ef7e82bdd3f6fc40e4b2aac6d3))
* initial nightwatch MVP ([2347be8](https://github.com/atriumn/noxaudit/commit/2347be8a0a2c9079739a1d134849ad2d60123f16))
* multi-retrieve idempotency + auto GitHub issues ([3543a1d](https://github.com/atriumn/noxaudit/commit/3543a1d057976a27fbdd8b57876803b4c10716da))
* persist structured findings to latest-findings.json and findings-history.jsonl ([#73](https://github.com/atriumn/noxaudit/issues/73)) ([fd5bb5f](https://github.com/atriumn/noxaudit/commit/fd5bb5f1252ffe8969bef96b433b83af71a35441))
* remove schedule/frames from OSS CLI, default --focus to all ([b3a8109](https://github.com/atriumn/noxaudit/commit/b3a8109f9764e56e4acd1872152cf2888f14332b))
* switch default provider from Anthropic to Gemini Flash ([016cfd8](https://github.com/atriumn/noxaudit/commit/016cfd82ea66b05db539716115fe88d081ab485a))
* wire SARIF output into CLI and runner (issue [#45](https://github.com/atriumn/noxaudit/issues/45)) ([#50](https://github.com/atriumn/noxaudit/issues/50)) ([2a27517](https://github.com/atriumn/noxaudit/commit/2a275175551b413ec41bd204089d67de9ce0a66d))


### Bug Fixes

* baseline --undo with filters silently removes nothing ([#53](https://github.com/atriumn/noxaudit/issues/53)) ([d82b74c](https://github.com/atriumn/noxaudit/commit/d82b74cff99b95101db2853d52ad5d0204635e7d))
* **ci:** break draft-email loop by skipping if draft already exists ([6e0fb1c](https://github.com/atriumn/noxaudit/commit/6e0fb1c6c3a362bec7311ae4aaf3c0e27f309d41))
* **ci:** use PAT in draft-email so push re-triggers CI checks ([6590a0a](https://github.com/atriumn/noxaudit/commit/6590a0a503c084af0e296f4234eb91f58186c138))
* correct .gitignore formatting for Ralph files ([468f249](https://github.com/atriumn/noxaudit/commit/468f24998a4f93b13993cc0b364a26b3effe5d9d))
* cost tracking projected monthly calculation and cache token handling ([#54](https://github.com/atriumn/noxaudit/issues/54)) ([6aea210](https://github.com/atriumn/noxaudit/commit/6aea21099b04c35900c92e6bcb066f0b745d0d75))
* enable pymdownx.emoji extension for Material icon rendering ([1503cbf](https://github.com/atriumn/noxaudit/commit/1503cbf22b08bbe7e64962221c7075474ed33f57))
* make GeminiProvider import conditional for optional google-genai dependency ([8fa563d](https://github.com/atriumn/noxaudit/commit/8fa563d288be627ee152745b1582d983ee5ef8c0))
* pre-push hook installs dev and mcp extras before running tests ([883cb62](https://github.com/atriumn/noxaudit/commit/883cb62147c1e25464c38ceeb22b072ca30fb34c))
* rename remaining Nightwatch references to Noxaudit ([3564560](https://github.com/atriumn/noxaudit/commit/3564560bfa492d252b5ef4d1a9d9e2c39e9fc299))
* resolve CI failures for ruff formatting and mcp import ([6b0a801](https://github.com/atriumn/noxaudit/commit/6b0a801f99670049ccf762b44f667040c849edb6))
* wire pre-pass execution into runner and commit prepass module ([#51](https://github.com/atriumn/noxaudit/issues/51)) ([d0840fa](https://github.com/atriumn/noxaudit/commit/d0840fac7f1f23dc7197694e29aedf55db5c0b56))
* wire pre-pass execution into runner and commit prepass module ([#52](https://github.com/atriumn/noxaudit/issues/52)) ([aba462b](https://github.com/atriumn/noxaudit/commit/aba462ba5ce41527a59ab8ca3f8f3ed63611b389))


### Miscellaneous

* add .ralph-fix-prompt.txt to .gitignore ([a2f7b6b](https://github.com/atriumn/noxaudit/commit/a2f7b6b69d578b40465b8de9dafd3b19377b437e))
* add .ralph/ to .gitignore (Ralph session files) ([f287cc9](https://github.com/atriumn/noxaudit/commit/f287cc9631031fa7dfad2049fe202faa8e69a751))
* add cryyer release email pipeline ([fb9a817](https://github.com/atriumn/noxaudit/commit/fb9a8179deddde8c10f3fea66ba11ea4e2dd17a0))
* add dependabot.yml with grouped minor/patch updates ([231b0cb](https://github.com/atriumn/noxaudit/commit/231b0cba3cdacce10ca44d79e7992712835ec483))
* add pre-commit and pre-push hooks for ruff and pytest ([#20](https://github.com/atriumn/noxaudit/issues/20)) ([e54291c](https://github.com/atriumn/noxaudit/commit/e54291c6081b90d257553deb6d92eb6588548f9b))
* add pre-commit and pre-push hooks for ruff and pytest ([#20](https://github.com/atriumn/noxaudit/issues/20)) ([5d570d3](https://github.com/atriumn/noxaudit/commit/5d570d3f0718019973034639c2d608abe1e92599))
* add Ralph monitor/prompt files to .gitignore ([e910abc](https://github.com/atriumn/noxaudit/commit/e910abcb7c87b953aa1e8759b307e48430c370e6))
* add release-please for automated versioning and changelogs ([0378986](https://github.com/atriumn/noxaudit/commit/03789863778741a0f5691a535d734ecb610f8921))
* auto-commit before merge (loop primary) ([43f4366](https://github.com/atriumn/noxaudit/commit/43f43662168cfed98859247180ddc27da6ff37b5))
* **deps:** bump actions/checkout from 4 to 6 ([feb0073](https://github.com/atriumn/noxaudit/commit/feb0073fe4779c6309ce18b4663831e1b239db7b))
* **deps:** bump actions/checkout from 4 to 6 ([94026ea](https://github.com/atriumn/noxaudit/commit/94026ea2c1756bc6d409b31dc260b9057ec90e7f))
* **deps:** bump actions/checkout from 4 to 6 ([#84](https://github.com/atriumn/noxaudit/issues/84)) ([7aa6a89](https://github.com/atriumn/noxaudit/commit/7aa6a8913db94ced82930033f214a62a57104c25))
* **deps:** bump actions/download-artifact from 4 to 8 ([#83](https://github.com/atriumn/noxaudit/issues/83)) ([c4988a6](https://github.com/atriumn/noxaudit/commit/c4988a635c54d5649a331e9d7b45d11ba51f5022))
* **deps:** bump actions/setup-python from 5 to 6 ([d6c98ee](https://github.com/atriumn/noxaudit/commit/d6c98ee7a310135b6bb6c879a7600854ad49d962))
* **deps:** bump actions/setup-python from 5 to 6 ([4f46cf5](https://github.com/atriumn/noxaudit/commit/4f46cf508fd805dc1daa7c5e206b42ef38152943))
* **deps:** bump actions/setup-python from 5 to 6 ([#86](https://github.com/atriumn/noxaudit/issues/86)) ([921cde3](https://github.com/atriumn/noxaudit/commit/921cde3ea76d302592369fa95b2e0730bf5666f8))
* **deps:** bump actions/upload-artifact from 4 to 7 ([#82](https://github.com/atriumn/noxaudit/issues/82)) ([c1983ff](https://github.com/atriumn/noxaudit/commit/c1983ff4af4c98bd71521532c61bc248a3780972))
* **deps:** bump astral-sh/setup-uv from 5 to 7 ([d6cb39f](https://github.com/atriumn/noxaudit/commit/d6cb39f950e7462eeb00728e415ac963f665fac6))
* **deps:** bump astral-sh/setup-uv from 5 to 7 ([55a2ba5](https://github.com/atriumn/noxaudit/commit/55a2ba5075ddb44db50957ce517842dd468a4aba))
* **deps:** bump astral-sh/setup-uv from 5 to 7 ([#85](https://github.com/atriumn/noxaudit/issues/85)) ([edc0471](https://github.com/atriumn/noxaudit/commit/edc0471d5ebadb2c9b09ae4b9e38634d52e4cff7))
* group github-actions minor/patch dependabot updates ([8724411](https://github.com/atriumn/noxaudit/commit/8724411d31ea54d476f4ee7dfab9c0b5eb639eec))
* remove Ralph session artifacts from git tracking ([a2c1ffb](https://github.com/atriumn/noxaudit/commit/a2c1ffbf76aae0d889ca3ea2fd1bdd6fe25be99b))


### Documentation

* add CHANGELOG.md documenting rename and initial release ([61856d0](https://github.com/atriumn/noxaudit/commit/61856d06b5aa809e1d5d769dddd69d14fd8a2690))
* add CONTRIBUTING.md for open source contributors ([5cdeee9](https://github.com/atriumn/noxaudit/commit/5cdeee99a737516ad1ec8803f0eb4817c63453ff))
* add GitHub Actions workflow example for nightly audits ([#72](https://github.com/atriumn/noxaudit/issues/72)) ([6274dc2](https://github.com/atriumn/noxaudit/commit/6274dc2d6050ccebc26162fc55bbb930d2f0feb9))
* add logo to README ([e019440](https://github.com/atriumn/noxaudit/commit/e0194403b604cbfa012adbb0c9d541e1a9fa6315))
* add MkDocs Material documentation site ([d371b24](https://github.com/atriumn/noxaudit/commit/d371b24c0356d391b7660a9a3cddb835d0b9b698))
* consolidate provider configuration in README ([#70](https://github.com/atriumn/noxaudit/issues/70)) ([2b7176f](https://github.com/atriumn/noxaudit/commit/2b7176f2e1059918be64b33641b3cf2fbc4f8a31))
* update README.md with Noxaudit branding ([a03dca8](https://github.com/atriumn/noxaudit/commit/a03dca82a4594ce955c5864bd593fef8f07b74a9))


### Code Refactoring

* make issues footer configurable and fix remaining nightwatch refs ([ba3f606](https://github.com/atriumn/noxaudit/commit/ba3f60683086eb1223dc4e3635ac87a7d733262f))
* rename config file and update .gitignore ([872c3ef](https://github.com/atriumn/noxaudit/commit/872c3ef12af9f8bad52db2209ead7b10211c8721))
* Rename nightwatch → noxaudit for open source release ([82fa94d](https://github.com/atriumn/noxaudit/commit/82fa94dcc6c79d6c7c79fe0f11411c16e64ebdc4))
* rename nightwatch/ directory to noxaudit/ ([f85f095](https://github.com/atriumn/noxaudit/commit/f85f09584943ac8f3debb8ecada9e02831357d89))
* rework all 7 focus prompts for thoroughness and coverage ([f670cf2](https://github.com/atriumn/noxaudit/commit/f670cf2cfe586f7ce6f2ffd4754e1d34b262b82c))
* update all Python imports from nightwatch to noxaudit ([d6dab14](https://github.com/atriumn/noxaudit/commit/d6dab14c2e3098c3576d0b663fbbe7f25e9b8f39))
* update GitHub Action and CI workflow for noxaudit rename ([8929216](https://github.com/atriumn/noxaudit/commit/89292164ba1a1825e901a8f0df8f0201ab937875))
* update pyproject.toml for noxaudit rename ([2fe1e0d](https://github.com/atriumn/noxaudit/commit/2fe1e0d94e9e0190f31fa35891c1e1e667d8a5bd))

## [Unreleased]

### Changed
- Renamed project from Nightwatch to Noxaudit for better GitHub uniqueness
- Package name changed from `nightwatch-ai` to `noxaudit`
- CLI command changed from `nightwatch` to `noxaudit`
- Configuration file renamed from `nightwatch.yml` to `noxaudit.yml`
- Working directory changed from `.nightwatch/` to `.noxaudit/`
- Made GitHub issue footer repository URL configurable via `repository_url` config field

## [0.1.0] - 2026-02-15

### Added
- Initial release
- Multi-provider AI support (Anthropic, Google Gemini)
- Rotating focus areas: security, patterns, docs, hygiene, performance, dependencies, testing
- Decision memory system to avoid re-flagging resolved issues
- GitHub Actions integration
- Telegram notifications
- GitHub issue creation
- Two-pass audit for large codebases
