# Changelog

## [2.0.1](https://github.com/quokkify/java-test-automation-template/compare/v2.0.0...v2.0.1) (2026-11-07)


### 🧹 Chores

* **template:** update shared project template ([#58](https://github.com/quokkify/java-test-automation-template/issues/58)) ([1cdc156](https://github.com/quokkify/java-test-automation-template/commit/1cdc156edb7e9120fadff878e969f0195c181608))

## [2.0.0](https://github.com/quokkify/java-test-automation-template/compare/v1.4.0...v2.0.0) (2026-11-07)

<!-- project-toolkit:release-notes v2 -->
**At a glance:** ⚠️ 1 breaking · 1 fixed · 5 updated · 31 internal

### ⚠️ Breaking changes

> [!WARNING]
> replace the q4j architecture gate with the ArchGate plugin ([#53](https://github.com/quokkify/java-test-automation-template/pull/53))
>
> Breaking change. Projects generated before 2.0.0:
>
> **After the update, the project has no architecture gate.** The migration removes the q4j gate but does not apply the ArchGate plugin. The gate stays disabled until section 3 of `docs/agents/architecture-verification.md` is done.
>
> 1. `copier update --trust --vcs-ref v2.0.0` (or later). The migration removes the old gate, and the build works again without it. Fix every `WARNING` line it prints.
> 2. Follow section 3 of `docs/agents/architecture-verification.md`: add the `archgate` version, library and plugin to the catalog; apply `alias(libs.plugins.archgate)` and the `archgate { }` block in `build.gradle`; add the two `testImplementation` lines; check that the services file exists.
> 3. Replace `verifyArchitecture` with `archgateCheck` in CI task lists.

### 🐛 Fixed

- **release:** show dependency updates in release notes ([#32](https://github.com/quokkify/java-test-automation-template/pull/32))

### ⬆️ Updated

- q4j 0.9.0 → 0.12.2 ([#18](https://github.com/quokkify/java-test-automation-template/pull/18), [#21](https://github.com/quokkify/java-test-automation-template/pull/21), [#23](https://github.com/quokkify/java-test-automation-template/pull/23), [#24](https://github.com/quokkify/java-test-automation-template/pull/24), [#26](https://github.com/quokkify/java-test-automation-template/pull/26))

<details><summary>Internal changes (31 PRs)</summary>

**Dependencies**

- actions/setup-java v6.0.1 → v6.1.0 ([#28](https://github.com/quokkify/java-test-automation-template/pull/28))
- actions/setup-python v7.0.0 → v7.1.0 ([#48](https://github.com/quokkify/java-test-automation-template/pull/48))
- checkstyle 14.3.0 → 14.4.0 ([#51](https://github.com/quokkify/java-test-automation-template/pull/51))
- com.github.spotbugs 6.5.12 → 6.5.13 ([#27](https://github.com/quokkify/java-test-automation-template/pull/27))
- gradle 9.8.0 → 9.8.2 ([#22](https://github.com/quokkify/java-test-automation-template/pull/22), [#41](https://github.com/quokkify/java-test-automation-template/pull/41))
- org.aspectj:aspectjweaver 1.9.25.1 → 1.9.27 ([#47](https://github.com/quokkify/java-test-automation-template/pull/47), [#55](https://github.com/quokkify/java-test-automation-template/pull/55))
- python 3.14 → 3.15 ([#29](https://github.com/quokkify/java-test-automation-template/pull/29))

**Maintenance**

- **ci-kit:** hand off base, security, release, allure, renovate to modules ([#43](https://github.com/quokkify/java-test-automation-template/pull/43))
- **ci-kit:** hand off validate to core module ([#31](https://github.com/quokkify/java-test-automation-template/pull/31))
- **renovate:** update q4j immediately ([#17](https://github.com/quokkify/java-test-automation-template/pull/17))
- **template:** update shared project template (19 PRs, [#15](https://github.com/quokkify/java-test-automation-template/pull/15)–[#57](https://github.com/quokkify/java-test-automation-template/pull/57))

</details>

## [1.4.0](https://github.com/quokkify/java-test-automation-template/compare/v1.3.0...v1.4.0) (2026-10-06)

<!-- project-toolkit:rich-block:start -->
<!-- project-toolkit:rich-release-notes pr=13 -->
### ✨ Highlights
Projects generated from the template publish every test to Allure with its q4j steps. The agent spec says how CI must upload the results.

### 🔄 Migration
`copier update` adds `gradle/allure.gradle` and the spec. To finish adoption, follow section 3 of `docs/agents/test-reporting.md`:
- add the `aspectj` catalog entries;
- apply `gradle/allure.gradle`;
- ignore `allure-results/`;
- upload `build/allure-results` from CI.
<!-- project-toolkit:rich-block:end -->

### Features

* publish every test to Allure with its steps ([#13](https://github.com/quokkify/java-test-automation-template/issues/13)) ([1da2229](https://github.com/quokkify/java-test-automation-template/commit/1da2229967e403bbfbffc449b2e2038104ecf896))

## [1.3.0](https://github.com/quokkify/java-test-automation-template/compare/v1.2.0...v1.3.0) (2026-10-06)

<!-- project-toolkit:rich-block:start -->
<!-- project-toolkit:rich-release-notes pr=11 -->
### ✨ Highlights
Generated projects run their tests in parallel through the q4j TestNG extensions, with retries. Agents get a spec for test execution and must use `HttpStatus` constants for status codes.

### 🔄 Migration
`copier update` adds `org.testng.ITestNGListener` and the spec when they are missing. To finish adoption, follow section 3 of `docs/agents/test-execution.md`:
- add `q4j-testng`;
- replace TestNG groups with package `include`/`exclude` or `@TestGroup`;
- replace status literals with `HttpStatus` constants.
<!-- project-toolkit:rich-block:end -->

### Features

* run tests through q4j TestNG extensions and name HTTP statuses ([#11](https://github.com/quokkify/java-test-automation-template/issues/11)) ([52493f9](https://github.com/quokkify/java-test-automation-template/commit/52493f952c9750999173deec6b9718bff187e36d))

## [1.2.0](https://github.com/quokkify/java-test-automation-template/compare/v1.1.0...v1.2.0) (2026-10-05)

<!-- project-toolkit:rich-block:start -->
<!-- project-toolkit:rich-release-notes pr=8 -->
### ✨ Highlights
Projects generated from the template verify their architecture on every `./gradlew check`. `AGENTS.md` points coding agents to a spec that tells them how to adopt the gate in older projects and how to fix each finding.

### 🔄 Migration
Existing projects get the spec, `gradle/architecture.gradle`, `tools/architecture/` and, if missing, `gradle.properties` with `copier update`. To finish adoption, an agent or a person follows section 3 of `docs/agents/architecture-verification.md`: raise q4j to 0.9.0, add the catalog entries, and apply the script from `build.gradle`.
<!-- project-toolkit:rich-block:end -->

### Features

* enable q4j architecture verification ([#8](https://github.com/quokkify/java-test-automation-template/issues/8)) ([1d53c1a](https://github.com/quokkify/java-test-automation-template/commit/1d53c1a86ac9c48ba872c7b69f98c29fbf3ad0d4))


### Bug Fixes

* order starter test imports for every base package ([#9](https://github.com/quokkify/java-test-automation-template/issues/9)) ([abca592](https://github.com/quokkify/java-test-automation-template/commit/abca59219b41181f97f5947abb454c6e7203c0fd))

## [1.1.0](https://github.com/quokkify/java-test-automation-template/compare/v1.0.0...v1.1.0) (2026-10-05)

<!-- project-toolkit:rich-block:start -->
<!-- project-toolkit:rich-release-notes pr=6 -->
### 💡 Usage Examples
```sh
copier copy --vcs-ref <tag> gh:quokkify/java-test-automation-template test-automation \
  -d package_root=dev.quokkify -d package_name=marketdesk
# → src/main/java/dev/quokkify/marketdesk/{config,model,service,helper,verification,step}
#   src/test/java/dev/quokkify/marketdesk/test
```

### 🔄 Migration
Run `copier update`. When it asks for `package_root`/`package_name`, answer with your existing base package. Delete the starter files you do not need, and move your classes into the generated packages. The template README covers this. Unmodified files of the old `example` starter and `CLAUDE.md` are removed by the update.
<!-- project-toolkit:rich-block:end -->

### Features

* agent authoring guide and generated package skeleton ([#6](https://github.com/quokkify/java-test-automation-template/issues/6)) ([03cfbd9](https://github.com/quokkify/java-test-automation-template/commit/03cfbd968fa07f3e3ab76fd1434f0b6598354ef7))

## 1.0.0 (2026-10-04)


### Features

* add Java test automation Copier template ([#1](https://github.com/quokkify/java-test-automation-template/issues/1)) ([2d873b5](https://github.com/quokkify/java-test-automation-template/commit/2d873b59e838e94aee6e6268211a2749cc04a7ab))
