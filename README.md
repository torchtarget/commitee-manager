# Committee Allocation Tool

A **personal, offline** Python tool that **allocates people to committees** under explicit rules, produces a **proposed full assignment**, and explains *why* each assignment was made.  

- **Primary user**: a single decision-maker  
- **Scale**: ~60 people, ~25 committees, ~10 rules  
- **Output**: a complete proposed allocation + per-seat rationales + committee health summaries  
- **Interaction model**: run scenarios, optionally lock some choices, tweak rule weights, re-allocate, compare

---

## Setup

1. Create a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Run the tests to verify the installation:

```bash
pytest
```


### Sample Data

Sample CSV and YAML files are provided in the `examples/` directory:

**people.csv**

```csv
name,service_cap,competencies
Alice,2,finance;strategy
Bob,1,
Carol,1,strategy
Dave,1,finance
```

**committees.csv**

```csv
name,min_size,max_size,required_competencies
Finance,1,2,finance
Strategy,1,2,strategy
Operations,1,1,
```

**rules.yaml**

```yaml
- name: service_cap
  kind: hard
  priority: 1
  params: {}
  explain_exclude: "{person.name} is at capacity"
- name: has_competency
  kind: soft
  priority: 2
  weight: 1
  params:
    competency: finance
  explain_score: "{person.name} has finance competency"
- name: has_competency
  kind: soft
  priority: 2
  weight: 1
  params:
    competency: strategy
  explain_score: "{person.name} has strategy competency"
```

### CLI Usage

Run the allocator over the sample files:

```bash
python -m committee_manager.cli.main allocate --people examples/people.csv --committees examples/committees.csv --rules examples/rules.yaml --output output_dir
```

The command writes `allocation.yaml` and `rationale.yaml` to `output_dir`.

---

## 1. Scope & Philosophy

- Offline, file-based (CSV + YAML inputs/outputs).  
- Transparent: every seat has a rationale; every exclusion has a reason.  
- Deterministic: same input = same output.  
- Private: all local, no network calls.  

Non-goals (MVP): meeting logistics, notifications, user management, databases.

---

## 2. Core Domain Objects

### Person

Represents one shareholder in the pool.

**Attributes**
- `id: str`
- `name: str`
- `age: int`
- `sex: Literal["F","M","Other"]`
- `family_branch: str`
- `competencies: set[str]`  
- `executive_role: bool`
- `conflicts: set[str]`
- `current_committees: set[str]`
- `service_cap: int`
- `cooling_off: dict[str, date]`
- `notes: str`

**Methods**
- `workload() -> int`
- `has_competency(comp: str) -> bool`

### Committee

Represents one committee to be filled.

**Attributes**
- `id: str`
- `name: str`
- `size_min: int`
- `size_max: int`
- `required_competencies: dict[str, int]`
- `desired_competencies: dict[str, int]`
- `hard_exclusions: set[str]`
- `diversity_targets: dict`
- `rotation_years: int`
- `current_members: list[tuple[str, date, date]]`
- `locked_members: set[str]`

**Methods**
- `current_coverage(assignees: set[Person]) -> CoverageSnapshot`

---

## 3. Rules & Scoring

### Rule Types
- **Hard constraints**: if violated, person is ineligible for that committee.  
- **Soft preferences**: add positive/negative points depending on how a candidate affects committee health.  

### Example Rule Library

**Hard**
1. Minimum age per committee  
2. Executive exclusion  
3. No siblings on same committee  
4. Capacity cap  
5. Cooling-off period  

**Soft**
6. Competency coverage  
7. Branch diversity  
8. Gender balance band  
9. Tenure mix  
10. Conflict overlap penalty  

### Rule Definition (YAML)
Each rule has:
- `name`, `kind (hard|soft)`, `priority`, `weight` (soft only), `applies_to`, `params`  
- Explanation templates: `explain_exclude`, `explain_score`

---

## 4. Allocation Engine

### Inputs
- People  
- Committees  
- Rule set (YAML)  
- Scenario (optional)  

### Steps
1. **Feasibility pre-check**: eligible pool per committee, detect impossible cases.  
2. **Greedy allocation**: fill seats starting with hardest committees; pick highest marginal score.  
3. **Local improvement pass**: bounded swaps/drops to improve total health.  
4. **Result packing**: allocation + rationales + health summaries.  

### Rationale Cards
Per seat:
