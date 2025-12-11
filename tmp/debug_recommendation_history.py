from pprint import pformat

from app.backend.database import DATABASE_URL, SessionLocal
from app.backend.models import Recipe, UserRecipeHistory
from app.backend.services.recommendation.data_source import (
    FEATURE_DIMENSIONS,
    RecipeDataSource,
)

print("DATABASE_URL=", DATABASE_URL)

sess = SessionLocal()
try:
    print("\n=== recipes (sample 20) ===")
    recipes = sess.query(Recipe).limit(20).all()
    print("count (fetched up to 20)=", len(recipes))
    for r in recipes:
        rid = getattr(r, "recipe_id", None)
        name = getattr(r, "recipe_name", None)
        flags = {f: bool(getattr(r, f, False)) for f in FEATURE_DIMENSIONS}
        nonzero = [k for k, v in flags.items() if v]
        print(f"  id={rid} name={name!r} nonzero_flags={nonzero}")

    print("\n=== user_recipe_history (user_id=1 sample 50) ===")
    history = (
        sess.query(UserRecipeHistory)
        .filter(UserRecipeHistory.user_id == 1)
        .limit(50)
        .all()
    )
    print("history count (fetched up to 50)=", len(history))
    for h in history:
        print(
            "  history_id=",
            getattr(h, "history_id", None),
            " recipe_id=",
            getattr(h, "recipe_id", None),
            " cooked_at=",
            getattr(h, "cooked_at", None),
            " servings=",
            getattr(h, "servings", None),
        )

    print(
        "\n=== build local recipe vector map via RecipeDataSource.load_and_vectorize_recipes() ==="
    )
    ds = RecipeDataSource(db_session=sess)
    all_recipes = ds.load_and_vectorize_recipes()
    print("loaded recipe objects count=", len(all_recipes))
    sample_map_keys = list(ds._recipe_vector_map.keys())[:20]
    print("recipe_vector_map keys sample=", sample_map_keys)

    print("\n=== create_user_profile_vector(user_id=1) result ===")
    vec = ds.create_user_profile_vector(1)
    print("vector (len=", len(vec), ")=", vec.tolist())
    nz = [
        (i, FEATURE_DIMENSIONS[i], float(vec[i]))
        for i in range(len(vec))
        if vec[i] != 0
    ]
    print("nonzero indices=", pformat(nz))

finally:
    sess.close()
