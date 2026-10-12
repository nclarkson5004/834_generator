from __future__ import annotations

from dataclasses import dataclass, field

from utils import upper

from x12_constants import (
    GENDER_CODES,
    INSURANCE_LINE_CODES,
    MAINTENANCE_TYPES,
    MARITAL_STATUS_CODES,
    RELATIONSHIP_CODES,
)


# =============================================================================
# COVERAGE
# =============================================================================


@dataclass(slots=True)
class Coverage:
    plan_type: str = ""
    plan_name: str = ""

    carrier: str = ""

    policy_number: str = ""
    subgroup_number: str = ""

    coverage_tier: str = ""

    effective_date: str = ""
    end_date: str = ""

    election_status: str = ""
    action: str = ""

    employee_contribution: str = ""
    employer_contribution: str = ""
    employee_cost: str = ""

    @property
    def insurance_line_code(self) -> str:
        return INSURANCE_LINE_CODES.get(
            upper(self.plan_type),
            upper(self.plan_type),
        )

    @property
    def maintenance_type(self) -> str:
        return MAINTENANCE_TYPES.get(
            upper(self.action),
            MAINTENANCE_TYPES["ADD"],
        )

    @property
    def is_active(self) -> bool:
        return self.end_date == ""

    @property
    def is_waived(self) -> bool:
        return upper(self.election_status) == "WAIVED"

    @property
    def is_medical(self) -> bool:
        return upper(self.plan_type) == "MEDICAL"

    @property
    def is_dental(self) -> bool:
        return upper(self.plan_type) == "DENTAL"

    @property
    def is_vision(self) -> bool:
        return upper(self.plan_type) == "VISION"

    @property
    def is_life(self) -> bool:
        return "LIFE" in upper(self.plan_type)


# =============================================================================
# PERSON
# =============================================================================


@dataclass(slots=True)
class Person:
    relationship: str = ""
    relationship_code: str = ""

    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""

    member_id: str = ""
    ssn: str = ""

    gender: str = ""
    birth_date: str = ""

    address1: str = ""
    address2: str = ""

    city: str = ""
    state: str = ""
    zip_code: str = ""

    county: str = ""
    country: str = "US"

    email: str = ""

    home_phone: str = ""
    mobile_phone: str = ""
    work_phone: str = ""

    marital_status: str = ""

    disabled: str = ""
    tobacco_user: str = ""

    student_status: str = ""

    medicare_a_date: str = ""
    medicare_b_date: str = ""
    medicare_c_date: str = ""
    medicare_d_date: str = ""

    coverages: list[Coverage] = field(default_factory=list)

    def add_coverage(self, coverage: Coverage) -> None:
        self.coverages.append(coverage)

    @property
    def full_name(self) -> str:
        return " ".join(
            part
            for part in (
                self.first_name,
                self.middle_name,
                self.last_name,
            )
            if part
        )

    @property
    def normalized_relationship(self) -> str:
        return RELATIONSHIP_CODES.get(
            upper(self.relationship),
            self.relationship_code or "G8",
        )

    @property
    def normalized_gender(self) -> str:
        return GENDER_CODES.get(
            upper(self.gender),
            "U",
        )

    @property
    def normalized_marital_status(self) -> str:
        return MARITAL_STATUS_CODES.get(
            upper(self.marital_status),
            "",
        )

    @property
    def is_employee(self) -> bool:
        return self.normalized_relationship == "18"

    @property
    def is_spouse(self) -> bool:
        return self.normalized_relationship == "01"

    @property
    def is_child(self) -> bool:
        return self.normalized_relationship == "19"

    @property
    def member_indicator(self) -> str:
        return "Y" if self.is_employee else "N"

    @property
    def maintenance_type(self) -> str:
        #
        # Full-file rule per companion guide: when BGN08=2 (full file), the
        # employee (subscriber) row must always be CHANGE (001). Only
        # dependents may vary between 001/021/024/025. See x12_constants.py
        # FULL_FILE_EMPLOYEE_MAINTENANCE_TYPE.
        #
        if self.is_employee:
            return MAINTENANCE_TYPES["CHANGE"]

        return MAINTENANCE_TYPES["ADD"]

    @property
    def maintenance_reason(self) -> str:
        return ""

    @property
    def relationship_value(self) -> str:
        return self.normalized_relationship

    @property
    def primary_coverage(self) -> Coverage | None:
        if not self.coverages:
            return None

        return self.coverages[0]


# =============================================================================
# SUBSCRIBER
# =============================================================================


@dataclass(slots=True)
class Subscriber:
    subscriber_key: str

    company_name: str = ""

    employee_id: str = ""

    employee_status: str = ""
    employee_type: str = ""

    hire_date: str = ""
    termination_date: str = ""
    termination_type: str = ""

    department: str = ""
    division: str = ""
    job_title: str = ""

    benefit_eligible_date: str = ""

    persons: list[tuple[str, Person]] = field(default_factory=list)

    def add_person(
        self,
        key: str,
        person: Person,
    ) -> Person:

        existing = self.get_person(key)

        if existing is not None:
            return existing

        self.persons.append((key, person))

        return person

    def get_person(
        self,
        key: str,
    ) -> Person | None:

        for existing_key, person in self.persons:

            if existing_key == key:
                return person

        return None

    @property
    def employee(self) -> Person:

        employees = [
            person
            for _, person in self.persons
            if person.is_employee
        ]

        if len(employees) != 1:
            raise ValueError(
                f"Subscriber {self.subscriber_key} must have exactly one employee."
            )

        return employees[0]

    @property
    def dependents(self) -> list[Person]:
        return [
            person
            for _, person in self.persons
            if not person.is_employee
        ]

    @property
    def all_people(self) -> list[Person]:
        return [
            person
            for _, person in self.persons
        ]

    @property
    def family_size(self) -> int:
        return len(self.persons)

    @property
    def has_dependents(self) -> bool:
        return len(self.dependents) > 0