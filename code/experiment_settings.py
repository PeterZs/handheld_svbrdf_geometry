from general_settings import path_localization
import collections.abc
import os
import json
from utils.logging import error

def localize_settings(settings, local_paths):
    local_settings = dict(settings)
    for path_key in local_paths:
        for data_key in local_settings:
            if isinstance(local_settings[data_key], str):
                local_settings[data_key] = local_settings[data_key].replace(path_key, local_paths[path_key])
            elif isinstance(local_settings[data_key], dict):
                local_settings[data_key] = localize_settings(local_settings[data_key], local_paths)
    return local_settings


def recursive_update(dictionary, updates):
    dictionary = dict(dictionary)
    for key, value in updates.items():
        if isinstance(value, collections.abc.Mapping):
            dictionary[key] = recursive_update(dictionary.get(key, {}), value)
        else:
            dictionary[key] = value
    return dictionary


class ExperimentSettings:
    def __init__(self, settings):
        self.settings = settings
    
    def localize(self):
        self.settings['local_data_settings'] = localize_settings(self.get('data_settings'), path_localization)
        self.settings['local_initialization_settings'] = localize_settings(self.get('initialization_settings'), path_localization)

    def save(self, name, index=None):
        full_name = name + ("" if index is None else "_%d" % index)
        os.makedirs(self.get('local_data_settings')['output_path'], exist_ok=True)
        settings_file = os.path.join(self.get('local_data_settings')['output_path'], "%s.json" % full_name)
        subsettings = self.get(name, index)
        with open(settings_file, "wt") as fh:
            return json.dump(subsettings, fh, indent=4)

    def get_state_folder(self, name, index=None):
        """
        Returns the folder name for the stored state for "name".
        """
        full_name = name + ("" if index is None else "_%d" % index)
        return os.path.join(
            self.settings['local_data_settings']['output_path'],
            "stored_states",
            full_name
        )

    def get(self, name, index=None):
        subsettings = self.settings[name]
        if index is not None:
            subsettings = subsettings[index]
            if name == "optimization_steps":
                subsettings = recursive_update(self.settings["default_optimization_settings"], subsettings)
        return subsettings

    def get_shorthand(self, name, index=None):
        if name != "optimization_steps" or index is None:
            return name
        else:
            optimization_settings = self.get(name, index)
            error("get_shorthand not implemented yet")

    def check_stored(self, name, index=None, non_critical=[]):
        """
        Checks if a stored settings file is available, reflecting that that step has been previously run.
        Returns False if no such settings are available, or True if they are available and match the provided settings.
        Raises an error if the stored settings are incompatible with the current settings.
        One can pass non-critical settings that don't necessarily need to match.
        """
        full_name = name + ("" if index is None else "_%d" % index)
        settings_file = os.path.join(self.settings['local_data_settings']['output_path'], "%s.json" % full_name)
        if os.path.exists(settings_file):
            with open(settings_file, "rt") as fh:
                stored_settings = json.load(fh)
            subsettings = self.get(name, index)
            if not (
                {k: v for k, v in subsettings.items() if k not in non_critical}
                ==
                {k: v for k, v in stored_settings.items() if k not in non_critical}
            ):
                error("The stored settings in '%s' are not compatible with the defined '%s'" % (
                    settings_file,
                    name + ("" if index is None else "[%d]" % index)
                ))
            else:
                return True
        else:
            return False