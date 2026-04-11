.PHONY: smoke-test-base smoke-test-collab smoke-test-combined

smoke-test-base:
	bash scripts/verify_compose_sku_profiles_smoke.sh base

smoke-test-collab:
	bash scripts/verify_compose_sku_profiles_smoke.sh collab

smoke-test-combined:
	bash scripts/verify_compose_sku_profiles_smoke.sh combined
