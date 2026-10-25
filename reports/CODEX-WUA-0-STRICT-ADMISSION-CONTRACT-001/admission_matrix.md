# Admission matrix — offline contract, native gates remain closed

Основной набор: 19 legacy +26 admission +7 mutant methods. Все конкретные коды — фиксированная диагностика, без пользовательского материала.

| Требование | Selector (AdmissionTests.test_...) | Конкретный отказ / разрешённый offline outcome | Native/security gap |
| --- | --- | --- | --- |
| Нет/пустой/неправильный users | missing_and_empty_users; auth_users_types_and_duplicate_references | AUTH_USERS_REQUIRED; AUTH_PRINCIPAL_INVALID; CREDENTIAL_REFERENCE_INVALID | Credential store/реальный auth не доказаны |
| Auth обязателен | auth_required_not_disabled_or_self_asserted | AUTH_REQUIRED; AUTH_MECHANISM_REQUIRED | Mechanism declaration не runtime proof |
| User/upstream refs | credential_reference_missing_wrong_or_inline_secret; upstream_reference_is_not_optional | CREDENTIAL_REFERENCE_INVALID; AUTH_USER_FIELDS; UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED | Никакого store lookup/secret delivery |
| Нет секретов в outputs | no_secrets_or_header_material_in_own_errors | AUTH_FIELDS; STRICT_INTERNAL_FAILURE; input text отсутствует | UPSTREAM_SECRET_BOUNDARY_UNVERIFIED, sing не патчился |
| CONNECT200 ≠ downstream | connect_acceptance_does_not_prove_route_or_owner; missing_metadata_and_handler_rejection_remain_explicit | CONNECT_DESTINATION_DENIED / CONNECT_METADATA_FIELDS; allowed intent всё равно BLOCKED | real_egress_verified=false |
| Method/Upgrade/plain | plain_http_upgrade_and_unknown_method; undeclared_connect_targets_and_uot_denied | CONNECT_METHOD_DENIED; CONNECT_UPGRADE_DENIED; CONNECT_POLICY_DENIED | Go parser не написан/не запускался |
| Exact D:port; IPv6 | exact_destination_and_port; logical_connect_target_is_distinct_from_physical_egress | CONNECT_ADDRESS_INVALID; CONNECT_PORT_INVALID; CONNECT_DESTINATION_DENIED | Не physical R:Q/owner proof |
| DIRECT/fallback/secondary/load balancing/default | direct_fallback_second_proxy_and_unknown_default | STRICT_DIRECT_DENIED; STRICT_FALLBACK_DENIED; STRICT_SECONDARY_PROXY_DENIED; STRICT_LOAD_BALANCER_DENIED; STRICT_DEFAULT_DENIED | Native route не проверен |
| DNS/UDP/IPv6/background/UoT | dns_udp_ipv6_health_telemetry_and_unknown_egress; undeclared_connect_targets_and_uot_denied | STRICT_EXTRA_EGRESS_DENIED; STRICT_UNDECLARED_ROUTE; CONNECT_POLICY_DENIED | Declarations не системный containment |
| Duplicate/unknown/null/canonical | duplicate_keys_unknown_fields_null_and_noncanonical_json; invalid_raw_types_and_parse_errors_are_fixed_codes | DUPLICATE_KEY; BROKER_SCHEMA; CONFIG_NOT_CANONICAL; JSON_SYNTAX; JSON_TYPE; STRICT_INPUT_TYPE | Native permissive decoder не policy oracle |
| Single protected source | protected_single_source_required | CONFIG_SINGLE_SOURCE_REQUIRED; CONFIG_PROTECTION_REQUIRED | CONFIG_SOURCE_PROTECTION_UNVERIFIED |
| Merge/reload/env | merge_reload_environment_override_denied | CONFIG_MERGE_DENIED; CONFIG_RELOAD_DENIED; CONFIG_ENV_OVERRIDE_DENIED | Actual filesystem/CLI/env enforcement pending |
| Config/source tamper | replacement_after_preflight_and_source_drift | CONFIG_PIN_MISMATCH; SOURCE_PIN_MISMATCH | Controller expected pins должны быть trusted |
| Self-authorized flags/engine/owner claims | data_cannot_enable_flags_or_authorize_evidence; unknown_engine_owner_and_runtime_claims_remain_blocked | BROKER_SCHEMA либо RUNTIME_SECURITY_UNVERIFIED; all activation false | Native owner/engine registry/WFP NOT VERIFIED |
| Metadata — не Go parser | metadata_is_not_a_go_parser_or_owner_attestation | CONNECT_METADATA_FIELDS | CONNECT_METADATA_ORACLE_UNVERIFIED |
| Schema remote ref | local_schema_cannot_trigger_remote_fetch | SCHEMA_EXTERNAL_REF без socket event | Ни fetch, ни listener |
| Исторический synthetic fixture | legacy_fixture_structural_valid_but_strict_blocked | BROKER_PROFILE_STRUCTURALLY_VALID + STRICT_ADMISSION_BLOCKED; strict call AUTH_USERS_REQUIRED | Совместимость не readiness |
| Полный корректный offline intent | complete_policy_cannot_promote_native_security; every_public_preflight_keeps_install_gate_blocked | strict_policy_status=VALID; policy_route_allowed=true; RUNTIME_SECURITY_UNVERIFIED | can_apply=false, can_start_tunnel=false, install_uninstall=BLOCKED |

Семь executed Python negative controls: auth guard, merge guard, method guard, route schema, canonical input, config pin, error echo. Каждый: один expected inner FAIL, ноль ERROR; outer check PASS при обнаружении ослабления. Эти тесты не являются native Go/Windows attack simulation.
