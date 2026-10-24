# Shared code

`checks/privacy.py` scans the entire repository, including every component and the published site. It is run once by the root check command. Device firmware, transport and gesture code stays with its owner until there is proven shared behavior.

Dependency folders (`.venv`, `venv`, `node_modules`) and derived `.noindex` folders are pruned before walking files. The tests check that dependency metadata is ignored while ordinary source in every component is still scanned.
