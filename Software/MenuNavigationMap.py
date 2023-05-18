from collections import OrderedDict

def get_menu_navigation_map():
    my_dict =  OrderedDict({
        "cv-gate-mod":OrderedDict(
        {"module a": {
            "data_pointer": None,
            "gate level": {
                "values": ["high", "low"],
                "attribute_name": "gate_level"
            },
            "cv max": {
                "values": ["10V","5V"],
                "attribute_name" : "cv_max"
            },
            "midi channel": {
                "values": ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
                "attribute_name" : "midi_channel"
            },
            "mod output": {
                "values": ["modulation", "velocity"],
                "attribute_name" : "mod_output"
            }
        },
            "module b": {
            "data_pointer": None,
            "gate level": {
                "values": ["high", "low"],
                "attribute_name": "gate_level"
            },
            "cv max": {
                "values": ["10V","5V"],
                "attribute_name" : "cv_max"
            },
            "midi channel": {
                "values": ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
                "attribute_name" : "midi_channel"
            },
            "mod output": {
                "values": ["modulation", "velocity"],
                "attribute_name" : "mod_output"
            }
        },
            "module c": {
            "data_pointer": None,
            "gate level": {
                "values": ["high", "low"],
                "attribute_name": "gate_level"
            },
            "cv max": {
                "values": ["10V","5V"],
                "attribute_name" : "cv_max"
            },
            "midi channel": {
                "values": ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
                "attribute_name" : "midi_channel"
            },
            "mod output": {
                "values": ["modulation", "velocity"],
                "attribute_name" : "mod_output"
            }
        },
            "module d": {
            "data_pointer": None,
            "gate level": {
                "values":  ["high", "low"],
                "attribute_name": "gate_level"
            },
            "cv max": {
                "values": ["10V","5V"],
                "attribute_name" : "cv_max"
            },
            "midi channel": {
                "values": ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
                "attribute_name" : "midi_channel"
            },
            "mod output": {
                "values": ["modulation", "velocity"],
                "attribute_name" : "mod_output"
            }

        }
        }),
        "mot pot":OrderedDict({}),
        "sync out":OrderedDict(
        {"data_pointer": None,
            "time division": {
                "values": ["1/4","1/4T","1/8","1/8T","1/16","1/16T","1/32","1/32T"],
                "attribute_name": "time_division"
            },
             "clock polarity": {
                "values": ["high pulse","low pulse", "invert"],
                "attribute_name": "clock_polarity"
            }
         })
    })
    return my_dict

