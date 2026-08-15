"""Meta-label research + portable live scorer."""
try:
    from .model import (  # noqa: F401
        JsonLogisticModel,
        LightGBMModel,
        MetaLabelModel,
        UntrainedModel,
        load_model,
        validate_artefact,
    )
    from .predict import (  # noqa: F401
        DEFAULT_ARTEFACT,
        FEATURES,
        load_artefact,
        predict_meta_prob,
    )
except ImportError:
    from model import (  # noqa: F401
        JsonLogisticModel,
        LightGBMModel,
        MetaLabelModel,
        UntrainedModel,
        load_model,
        validate_artefact,
    )
    from predict import (  # noqa: F401
        DEFAULT_ARTEFACT,
        FEATURES,
        load_artefact,
        predict_meta_prob,
    )
