from typing import List
from utils import LimitFilter
from models_db import Submission


def get_all_limits(
    base_limit: LimitFilter, locked_vis: bool = False
) -> List[LimitFilter]:
    # Get all permutations of visibilities and lockouts and return Limits for them
    # TODO: Non-root should actually include other content if settings say so
    # Also we need some way to allow a lockout to include all visibilities [explicit config?]
    def unique_limit(f: Submission) -> LimitFilter:
        return LimitFilter(
            visibility=f.visibility,
            visibilityOnly=locked_vis,
            lockout=f.lockout,
            lockoutOnly=locked_vis,
        )

    submissions = Submission.query.all()
    limits = set(map(unique_limit, submissions))
    return limits
