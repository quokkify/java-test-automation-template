# Changelog

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
