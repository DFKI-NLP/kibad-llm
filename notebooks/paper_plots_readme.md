# Configurations used with paper_plots.ipynb to produce the figures for the paper

## Main results (F1, P, R) across LLMs on the Faktencheck core schema
SCHEMA = "Faktencheck Core"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/525_faktencheck_core_bestconfig_testset/figure_data/faktencheck_core_f1_micro_flat-ALL-data.json"),
    },
]
SERIES_NAME_MAP = {
    "525_faktencheck_core_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": "ALL",  # or None
    "metric": "f1",  # or None
}

## F1, P, R across LLMs per variable on the Faktencheck core schema

per variable, replace in EXPERIMENTS: biodiversity_level, ecosystem_type.category, ecosystem_type.term, taxa.species_group, habitat

SCHEMA = "Faktencheck Core"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/525_faktencheck_core_bestconfig_testset/figure_data/faktencheck_core_f1_micro_flat-biodiversity_level-data.json"),
    },
]
SERIES_NAME_MAP = {
    "525_faktencheck_core_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": None,  # or None
    "metric": "f1",  # or None
}

## Main results (F1, P, R) across LLMs on the Organism trends schema
SCHEMA = "Organism Trends"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/549_organism_trends_bestconfig_testset/figure_data/organism_trends_f1_micro-ALL-data.json"),
    },
]
SERIES_NAME_MAP = {
    "549_organism_trends_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": "ALL",  # or None
    "metric": "f1",  # or None
}

## Results (F1, P, R) for base entries habitat and species group across LLMs on the Organism trends schema
SCHEMA = "Organism Trends (habitat and species group)"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/549_organism_trends_bestconfig_testset/figure_data/organism_trends_f1_micro_base_entries-ALL-data.json"),
    },
]
SERIES_NAME_MAP = {
    "549_organism_trends_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": "ALL",  # or None
    "metric": "f1",  # or None
}

## Results (F1, P, R) for biodiversity variable given habitat and species group across LLMs on the Organism trends schema
SCHEMA = "Organism Trends (biodiversity variable given habitat and species group)"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/549_organism_trends_bestconfig_testset/figure_data/organism_trends_f1_micro_conditional_variable_only-ALL-data.json"),
    },
]
SERIES_NAME_MAP = {
    "549_organism_trends_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": "ALL",  # or None
    "metric": "f1",  # or None
}

## Results (F1, P, R) for biodiversity variable and trend given habitat and species group across LLMs on the Organism trends schema
SCHEMA = "Organism Trends (biodiversity variable and trend given habitat and species group)"
EXPERIMENT_FILENAME = "test"
EXPERIMENTS = [
    {
        "path": Path("../../kibad-llm-results/logs/549_organism_trends_bestconfig_testset/figure_data/organism_trends_f1_micro_conditional_variable_and_trend-ALL-data.json"),
    },
]
SERIES_NAME_MAP = {
    "549_organism_trends_bestconfig_testset": "Test",
    #"519_faktencheck_core": "Dev",
}

EXPERIMENT_ORDER = None
SORT_BY = {
    "experiment": None,
    "variable": "ALL",  # or None
    "metric": "f1",  # or None
}