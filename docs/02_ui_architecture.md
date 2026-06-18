# 02. UI Architecture & Frontend

Located in the `ui/` directory, the SYNAPSE frontend is a highly responsive **PyQt6** application. Because it interfaces directly with a heavy, multi-threaded PyTorch backend, strict structural patterns are required to prevent the UI from freezing.

## The View-Controller Delegation (`MainWindow`)

The `MainWindow` (`ui/main_window.py`) does **not** contain direct layout code or widget instantiation for the bulk of the application. It acts purely as a structural foundation.

It delegates responsibilities to specialized components:
- **`CentralTabs`**: Manages the main workspace (Map View, Analytics, System Config).
- **`MainMenu`**: Manages the top menu bar.
- **`DockManager`**: Controls the floating tool windows (Log Console, Sensor Inspector).
- **`DialogHandler`**: Centralizes the logic for opening popups and configuration windows, preventing memory leaks from un-garbage-collected Qt dialogs.

## The Signal Router Matrix

One of the most complex problems in bridging PyQt6 and PyTorch is thread safety. PyTorch tensors are manipulated on background threads, but PyQt6 **requires** all UI updates to happen exclusively on the Main Thread.

SYNAPSE solves this via the **`SignalRouter`** (`ui/handlers/signal_router.py`):
1. When the `InferenceEngine` finishes a cycle, it emits `engine_global_results`.
2. This signal crosses the thread boundary and is caught by the `MainController`.
3. The `MainController` proxies it to the `SignalRouter`.
4. The `SignalRouter` safely unpacks the payload (stripping out heavy CUDA tensors and keeping only the numpy visualization arrays) and routes it to the specific UI widgets (like the Map renderer or the live charts).

This guarantees that a slow screen repaint will **never** cause the Neural Engine to miss its 1-second real-time deadline.

## User Experience Subsystems

### TranslationManager (`ui/utilities/translation_manager.py`)
SYNAPSE supports full i18n localization. Changing the language dynamically emits a `QEvent.Type.LanguageChange` event, which the `MainWindow` catches to recursively call `retranslate_ui()` down the entire widget tree without restarting the application.

### ThemeManager (`ui/styles/theme_manager.py`)
Supports dynamic Dark and Light modes by applying global `.qss` (Qt Style Sheets) at runtime.

### System Tray Integration
Traffic management systems run 24/7. When the user closes the main window, SYNAPSE intercepts the `closeEvent` and hides the window to the OS System Tray. The neural pipeline continues processing and transmitting to CARINA completely headless. A context menu allows the user to restore the UI or explicitly quit.
