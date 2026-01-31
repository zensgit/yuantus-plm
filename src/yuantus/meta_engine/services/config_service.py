from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from yuantus.meta_engine.models.configuration import (
    ConfigOption,
    ConfigOptionSet,
    OptionValueType,
    ProductConfiguration,
    VariantRule,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.config_validator import ConfigSelectionValidator


class ConfigService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def list_option_sets(
        self,
        item_type_id: Optional[str] = None,
        *,
        include_global: bool = True,
        include_inactive: bool = True,
    ) -> List[ConfigOptionSet]:
        query = self.session.query(ConfigOptionSet)
        if not include_inactive:
            query = query.filter(ConfigOptionSet.is_active.is_(True))
        if item_type_id:
            conditions = [ConfigOptionSet.item_type_id == item_type_id]
            if include_global:
                conditions.append(ConfigOptionSet.item_type_id.is_(None))
            query = query.filter(or_(*conditions))
        return query.order_by(ConfigOptionSet.sequence.asc(), ConfigOptionSet.name.asc()).all()

    def get_option_set(self, option_set_id: str) -> Optional[ConfigOptionSet]:
        return self.session.get(ConfigOptionSet, option_set_id)

    def get_option_set_by_name(self, name: str) -> Optional[ConfigOptionSet]:
        return (
            self.session.query(ConfigOptionSet)
            .filter(ConfigOptionSet.name == name)
            .first()
        )

    def create_option_set(self, payload: Dict[str, Any]) -> ConfigOptionSet:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("OptionSet name is required")

        existing = self.get_option_set_by_name(name)
        if existing:
            raise ValueError(f"OptionSet name already exists: {name}")

        option_set = ConfigOptionSet(
            id=payload.get("id") or str(uuid.uuid4()),
            name=name,
            label=payload.get("label") or name,
            description=payload.get("description"),
            value_type=payload.get("value_type") or OptionValueType.STRING.value,
            allow_multiple=bool(payload.get("allow_multiple", False)),
            is_required=bool(payload.get("is_required", False)),
            default_value=payload.get("default_value"),
            sequence=int(payload.get("sequence") or 0),
            item_type_id=payload.get("item_type_id"),
            is_active=bool(payload.get("is_active", True)),
            config=payload.get("config") or {},
            created_by_id=payload.get("created_by_id"),
        )
        self.session.add(option_set)
        self.session.flush()
        return option_set

    def update_option_set(self, option_set: ConfigOptionSet, payload: Dict[str, Any]) -> ConfigOptionSet:
        if "name" in payload and payload["name"]:
            name = payload["name"].strip()
            if name != option_set.name:
                existing = self.get_option_set_by_name(name)
                if existing and existing.id != option_set.id:
                    raise ValueError(f"OptionSet name already exists: {name}")
                option_set.name = name
        if "label" in payload:
            option_set.label = payload.get("label")
        if "description" in payload:
            option_set.description = payload.get("description")
        if "value_type" in payload:
            option_set.value_type = payload.get("value_type") or OptionValueType.STRING.value
        if "allow_multiple" in payload:
            option_set.allow_multiple = bool(payload.get("allow_multiple"))
        if "is_required" in payload:
            option_set.is_required = bool(payload.get("is_required"))
        if "default_value" in payload:
            option_set.default_value = payload.get("default_value")
        if "sequence" in payload:
            option_set.sequence = int(payload.get("sequence") or 0)
        if "item_type_id" in payload:
            option_set.item_type_id = payload.get("item_type_id")
        if "is_active" in payload:
            option_set.is_active = bool(payload.get("is_active"))
        if "config" in payload:
            option_set.config = payload.get("config") or {}
        self.session.add(option_set)
        self.session.flush()
        return option_set

    def delete_option_set(self, option_set: ConfigOptionSet, force: bool = False) -> None:
        if option_set.options and not force:
            raise ValueError("OptionSet has options; use force=1 to delete")
        self.session.delete(option_set)
        self.session.flush()

    def add_option(self, option_set: ConfigOptionSet, payload: Dict[str, Any]) -> ConfigOption:
        key = (payload.get("key") or "").strip()
        if not key:
            raise ValueError("Option key is required")

        existing = (
            self.session.query(ConfigOption)
            .filter(
                ConfigOption.option_set_id == option_set.id,
                ConfigOption.key == key,
            )
            .first()
        )
        if existing:
            raise ValueError(f"Option key already exists: {key}")

        option = ConfigOption(
            id=payload.get("id") or str(uuid.uuid4()),
            option_set_id=option_set.id,
            key=key,
            label=payload.get("label") or key,
            value=payload.get("value") or key,
            description=payload.get("description"),
            ref_item_id=payload.get("ref_item_id"),
            sort_order=int(payload.get("sort_order") or 0),
            is_default=bool(payload.get("is_default", False)),
            is_active=bool(payload.get("is_active", True)),
            extra=payload.get("extra"),
        )
        self.session.add(option)
        self.session.flush()
        return option

    def update_option(self, option: ConfigOption, payload: Dict[str, Any]) -> ConfigOption:
        if "key" in payload and payload["key"]:
            key = payload["key"].strip()
            if key != option.key:
                existing = (
                    self.session.query(ConfigOption)
                    .filter(
                        ConfigOption.option_set_id == option.option_set_id,
                        ConfigOption.key == key,
                    )
                    .first()
                )
                if existing and existing.id != option.id:
                    raise ValueError(f"Option key already exists: {key}")
                option.key = key
        if "label" in payload:
            option.label = payload.get("label")
        if "value" in payload:
            option.value = payload.get("value")
        if "description" in payload:
            option.description = payload.get("description")
        if "ref_item_id" in payload:
            option.ref_item_id = payload.get("ref_item_id")
        if "sort_order" in payload:
            option.sort_order = int(payload.get("sort_order") or 0)
        if "is_default" in payload:
            option.is_default = bool(payload.get("is_default"))
        if "is_active" in payload:
            option.is_active = bool(payload.get("is_active"))
        if "extra" in payload:
            option.extra = payload.get("extra")
        self.session.add(option)
        self.session.flush()
        return option

    def delete_option(self, option: ConfigOption) -> None:
        self.session.delete(option)
        self.session.flush()

    # ----------------------------------------------------------------------
    # Variant rules
    # ----------------------------------------------------------------------

    def list_variant_rules(
        self,
        *,
        parent_item_id: Optional[str] = None,
        parent_item_type_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[VariantRule]:
        query = self.session.query(VariantRule)
        if not include_inactive:
            query = query.filter(VariantRule.is_active.is_(True))

        conditions = []
        if parent_item_id:
            conditions.append(VariantRule.parent_item_id == parent_item_id)
        if parent_item_type_id:
            conditions.append(
                and_(
                    VariantRule.parent_item_id.is_(None),
                    VariantRule.parent_item_type_id == parent_item_type_id,
                )
            )
        if conditions:
            conditions.append(
                and_(
                    VariantRule.parent_item_id.is_(None),
                    VariantRule.parent_item_type_id.is_(None),
                )
            )
            query = query.filter(or_(*conditions))

        return query.order_by(VariantRule.priority.asc(), VariantRule.name.asc()).all()

    def get_variant_rule(self, rule_id: str) -> Optional[VariantRule]:
        return self.session.get(VariantRule, rule_id)

    def create_variant_rule(self, payload: Dict[str, Any]) -> VariantRule:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("VariantRule name is required")
        condition = self._normalize_condition(payload.get("condition"))
        if not condition:
            raise ValueError("VariantRule condition is required")

        action_type = (payload.get("action_type") or "").strip().lower()
        if action_type not in {"include", "exclude", "substitute", "modify_qty"}:
            raise ValueError("VariantRule action_type must be include|exclude|substitute|modify_qty")

        rule = VariantRule(
            id=payload.get("id") or str(uuid.uuid4()),
            name=name,
            description=payload.get("description"),
            parent_item_type_id=payload.get("parent_item_type_id"),
            parent_item_id=payload.get("parent_item_id"),
            condition=condition,
            action_type=action_type,
            target_item_id=payload.get("target_item_id"),
            target_relationship_id=payload.get("target_relationship_id"),
            action_params=payload.get("action_params") or {},
            priority=int(payload.get("priority") or 100),
            is_active=bool(payload.get("is_active", True)),
            created_by_id=payload.get("created_by_id"),
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def update_variant_rule(self, rule: VariantRule, payload: Dict[str, Any]) -> VariantRule:
        if "name" in payload and payload["name"]:
            rule.name = payload["name"].strip()
        if "description" in payload:
            rule.description = payload.get("description")
        if "parent_item_type_id" in payload:
            rule.parent_item_type_id = payload.get("parent_item_type_id")
        if "parent_item_id" in payload:
            rule.parent_item_id = payload.get("parent_item_id")
        if "condition" in payload:
            normalized = self._normalize_condition(payload.get("condition"))
            if not normalized:
                raise ValueError("VariantRule condition is required")
            rule.condition = normalized
        if "action_type" in payload:
            action_type = (payload.get("action_type") or "").strip().lower()
            if action_type not in {"include", "exclude", "substitute", "modify_qty"}:
                raise ValueError("VariantRule action_type must be include|exclude|substitute|modify_qty")
            rule.action_type = action_type
        if "target_item_id" in payload:
            rule.target_item_id = payload.get("target_item_id")
        if "target_relationship_id" in payload:
            rule.target_relationship_id = payload.get("target_relationship_id")
        if "action_params" in payload:
            rule.action_params = payload.get("action_params") or {}
        if "priority" in payload:
            rule.priority = int(payload.get("priority") or 100)
        if "is_active" in payload:
            rule.is_active = bool(payload.get("is_active"))
        self.session.add(rule)
        self.session.flush()
        return rule

    def delete_variant_rule(self, rule: VariantRule) -> None:
        self.session.delete(rule)
        self.session.flush()

    # ----------------------------------------------------------------------
    # Configuration evaluation
    # ----------------------------------------------------------------------

    def validate_selections(
        self,
        product_item_id: str,
        selections: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        product = self.session.get(Item, product_item_id)
        if not product:
            return False, ["Product not found"]

        option_sets = self.list_option_sets(
            product.item_type_id,
            include_global=True,
            include_inactive=False,
        )
        validator = ConfigSelectionValidator(option_sets)
        errors = validator.validate(selections or {})
        return len(errors) == 0, errors

    def get_effective_bom(
        self,
        product_item_id: str,
        selections: Dict[str, Any],
        *,
        levels: int = 10,
        effective_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        full_bom = self.bom_service.get_bom_structure(
            product_item_id,
            levels=levels,
            effective_date=effective_date,
            config_selection=None,
        )
        product = self.session.get(Item, product_item_id)
        rules = self.list_variant_rules(
            parent_item_id=product_item_id,
            parent_item_type_id=product.item_type_id if product else None,
            include_inactive=False,
        )
        return self._apply_variant_rules(full_bom, rules, selections or {})

    def _normalize_condition(self, condition: Any) -> Optional[Dict[str, Any]]:
        return self.bom_service._normalize_config_condition(condition)

    def evaluate_condition(self, condition: Dict[str, Any], selections: Dict[str, Any]) -> bool:
        return self.bom_service._evaluate_config_condition(condition, selections)

    def _rule_targets(self, rule: VariantRule, rel_id: Optional[str], child_id: Optional[str]) -> bool:
        if rule.target_item_id and rule.target_item_id == child_id:
            return True
        if rule.target_relationship_id and rule.target_relationship_id == rel_id:
            return True
        return rule.target_item_id is None and rule.target_relationship_id is None

    def _apply_variant_rules(
        self,
        bom: Dict[str, Any],
        rules: List[VariantRule],
        selections: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = dict(bom)
        children = bom.get("children") or []
        filtered_children: List[Dict[str, Any]] = []

        for child_entry in children:
            rel = child_entry.get("relationship") or {}
            child = child_entry.get("child") or {}
            rel_props = rel.get("properties") or {}
            rel_id = rel.get("id")
            child_id = child.get("id")

            include = True
            if "config_condition" in rel_props:
                include = self.bom_service._match_config_condition(
                    rel_props.get("config_condition"), selections
                )

            substitute_with: Optional[str] = None
            qty_multiplier = 1.0
            include_rule_present = False
            include_rule_matched = False

            for rule in rules:
                if not rule.is_active:
                    continue
                if not self._rule_targets(rule, rel_id, child_id):
                    continue
                if rule.action_type == "include":
                    include_rule_present = True
                if not self.evaluate_condition(rule.condition, selections):
                    continue

                if rule.action_type == "exclude":
                    include = False
                    break
                if rule.action_type == "include":
                    include_rule_matched = True
                elif rule.action_type == "substitute":
                    params = rule.action_params or {}
                    substitute_with = params.get("substitute_with")
                elif rule.action_type == "modify_qty":
                    params = rule.action_params or {}
                    try:
                        qty_multiplier = float(params.get("quantity_multiplier", qty_multiplier))
                    except (TypeError, ValueError):
                        qty_multiplier = qty_multiplier

            if include_rule_present and not include_rule_matched:
                include = False

            if not include:
                continue

            if substitute_with:
                sub_item = self.session.get(Item, substitute_with)
                if sub_item:
                    child = sub_item.to_dict()
                    child_entry = dict(child_entry)
                    child_entry["child"] = child
                    child_entry["substituted_from"] = child_id

            if qty_multiplier != 1.0:
                rel = dict(rel)
                props = dict(rel_props)
                qty = props.get("quantity", 1)
                try:
                    props["quantity"] = float(qty) * qty_multiplier
                except (TypeError, ValueError):
                    props["quantity"] = qty
                props["original_quantity"] = qty
                rel["properties"] = props
                child_entry = dict(child_entry)
                child_entry["relationship"] = rel

            if child.get("children"):
                child_entry = dict(child_entry)
                child_entry["child"] = self._apply_variant_rules(
                    child, rules, selections
                )

            filtered_children.append(child_entry)

        result["children"] = filtered_children
        return result

    # ----------------------------------------------------------------------
    # Product configurations
    # ----------------------------------------------------------------------

    def list_product_configurations(
        self, *, product_item_id: Optional[str] = None
    ) -> List[ProductConfiguration]:
        query = self.session.query(ProductConfiguration)
        if product_item_id:
            query = query.filter(ProductConfiguration.product_item_id == product_item_id)
        return query.order_by(ProductConfiguration.created_at.desc()).all()

    def get_product_configuration(self, config_id: str) -> Optional[ProductConfiguration]:
        return self.session.get(ProductConfiguration, config_id)

    def create_product_configuration(self, payload: Dict[str, Any]) -> ProductConfiguration:
        product_item_id = payload.get("product_item_id")
        name = (payload.get("name") or "").strip()
        selections = payload.get("selections") or {}
        if not product_item_id:
            raise ValueError("product_item_id is required")
        if not name:
            raise ValueError("Configuration name is required")

        is_valid, errors = self.validate_selections(product_item_id, selections)
        if not is_valid:
            raise ValueError("; ".join(errors))

        config = ProductConfiguration(
            id=payload.get("id") or str(uuid.uuid4()),
            product_item_id=product_item_id,
            name=name,
            description=payload.get("description"),
            selections=selections,
            state=payload.get("state") or "draft",
            version=int(payload.get("version") or 1),
            created_by_id=payload.get("created_by_id"),
        )
        self.session.add(config)
        self.session.flush()

        self._update_effective_bom_cache(config)
        return config

    def update_product_configuration(
        self, config: ProductConfiguration, payload: Dict[str, Any]
    ) -> ProductConfiguration:
        if "name" in payload and payload["name"]:
            config.name = payload["name"].strip()
        if "description" in payload:
            config.description = payload.get("description")
        if "state" in payload:
            config.state = payload.get("state") or config.state
        if "version" in payload:
            config.version = int(payload.get("version") or config.version)
        if "selections" in payload:
            selections = payload.get("selections") or {}
            is_valid, errors = self.validate_selections(config.product_item_id, selections)
            if not is_valid:
                raise ValueError("; ".join(errors))
            config.selections = selections
            self._update_effective_bom_cache(config)
        self.session.add(config)
        self.session.flush()
        return config

    def refresh_product_configuration(self, config: ProductConfiguration) -> ProductConfiguration:
        self._update_effective_bom_cache(config)
        self.session.add(config)
        self.session.flush()
        return config

    def _update_effective_bom_cache(self, config: ProductConfiguration) -> None:
        effective_bom = self.get_effective_bom(config.product_item_id, config.selections)
        config.effective_bom_cache = effective_bom
        config.cache_updated_at = datetime.utcnow()
        self.session.add(config)
