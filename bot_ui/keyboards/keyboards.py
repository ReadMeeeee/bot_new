from bot_ui.keyboards.keyboards_config import make_keyboard

# region main
start_main          = make_keyboard("menu", "main", include_back=False)
start_main_base     = make_keyboard("menu", "base")
start_main_group    = make_keyboard("menu", "group")
start_main_requests = make_keyboard("menu", "requests")
start_main_ai       = make_keyboard("menu", "ai")
# endregion

# region help
help_main           = make_keyboard("help", "main")
help_main_base      = make_keyboard("help", "base")
help_main_group     = make_keyboard("help", "group")
help_main_requests  = make_keyboard("help", "requests")
help_main_ai        = make_keyboard("help", "ai")
# endregion
