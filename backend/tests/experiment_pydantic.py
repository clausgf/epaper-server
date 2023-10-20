from pydantic import BaseModel
from typing import Any, Dict, Optional, List, Tuple, Literal, ClassVar, Union


class BaseWidget:
    pass


class BaseWidgetSettings(BaseModel):
    widget_class_reference: ClassVar[type[BaseWidget]] = BaseWidget
    widget_class: Literal[widget_class_reference.__name__]
    position: Tuple[int, int]


class TextWidget(BaseWidget):
    pass

class TextWidgetSettings(BaseWidgetSettings):
    widget_class_reference: ClassVar[type[BaseWidget]] = TextWidget
    widget_class: Literal["TextWidget"]
    pass

class DateWidget(BaseWidget):
    pass

class DateWidgetSettings(BaseWidgetSettings):
    widget_class_reference: ClassVar[type[BaseWidget]] = DateWidget
    widget_class: Literal["DateWidget"]
    pass


print("-"*40)
print("Inspecting settings class for ", BaseWidget.__name__)
print("class name: ", BaseWidgetSettings.__name__)
print("model fields: ", BaseWidgetSettings.model_fields)
print("widget class reference: ", BaseWidgetSettings.widget_class_reference.__name__)
print()
print("Inspecting settings class for ", TextWidget.__name__)
print("class name: ", TextWidgetSettings.__name__)
print("model fields: ", TextWidgetSettings.model_fields)
print("widget class reference: ", TextWidgetSettings.widget_class_reference.__name__)
print()
print("Inspecting settings class for ", DateWidget.__name__)
print("class name: ", DateWidgetSettings.__name__)
print("model fields: ", DateWidgetSettings.model_fields)
print("widget class reference: ", DateWidgetSettings.widget_class_reference.__name__)
print("*** end of preparation ***")

class EpaperSettings(BaseModel):
    widgets: List[Union[TextWidgetSettings, DateWidgetSettings]] = []

eps = EpaperSettings()
eps.widgets.append(TextWidgetSettings(widget_class="TextWidget", position=(0,0)))
eps.widgets.append(DateWidgetSettings(widget_class="DateWidget", position=(1,1)))
eps.widgets.append(TextWidgetSettings(widget_class="TextWidget", position=(2,2))) 
# serialize eps to yaml
import yaml
print(yaml.dump(eps.model_config))

print("*** Complete ***")
