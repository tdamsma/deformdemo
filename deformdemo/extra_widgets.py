"""Extra widgets."""
import json
from typing import Any, Dict, List, Tuple, Union
from uuid import uuid4

import colander
from deform.field import Field
from deform.widget import DateTimeInputWidget, ResourceRegistry
from deform.widget import Select2Widget
from deform.widget import SelectWidget
from deform.widget import Widget

resource_registry = ResourceRegistry(use_defaults=True)

# json editor
resource_registry.set_js_resources(
    "jsoneditor", None, "deformdemo:static/jsoneditor/jsoneditor.min.js"
)
resource_registry.set_css_resources(
    "jsoneditor",
    None,
    "deformdemo:static/jsoneditor/jsoneditor.min.css",
)

# jexcel
resource_registry.set_js_resources(
    "jexcel", None, "deformdemo:static/jexcel/jexcel.js"
)
resource_registry.set_css_resources(
    "jexcel", None, "deformdemo:static/jexcel/jexcel.css"
)
resource_registry.set_js_resources(
    "jsuites", None, "deformdemo:static/jexcel/jsuites.js"
)
resource_registry.set_css_resources(
    "jsuites", None, "deformdemo:static/jexcel/jsuites.css"
)

# react-jsonschema-form
resource_registry.set_js_resources(
    "rjsf-react",
    None,
    "deformdemo:static/react-jsonschema-form/react.js",
)
resource_registry.set_js_resources(
    "rjsf-react-dom",
    None,
    "deformdemo:static/react-jsonschema-form/react-dom.js",
)
resource_registry.set_js_resources(
    "rjsf",
    None,
    "deformdemo:static/react-jsonschema-form/react-jsonschema-form.js",
)


# select2sortable
resource_registry.set_js_resources(
    "html5sortable_for_select2sortable",
    None,
    "deformdemo:static/select2sortable/html.sortable.js",
)
resource_registry.set_js_resources(
    "select2_for_select2sortable",
    None,
    "deformdemo:static/select2sortable/select2.js",
)
resource_registry.set_css_resources(
    "select2_for_select2sortable",
    None,
    "deformdemo:static/select2sortable/select2.css",
)
resource_registry.set_js_resources(
    "select2sortable",
    None,
    "deformdemo:static/select2sortable/select2.sortable.js",
)
resource_registry.set_css_resources(
    "select2sortable",
    None,
    "deformdemo:static/select2sortable/select2.sortable.css",
)


class JsonWidget(Widget):
    """Json editor with schema validation.

    Based on https://github.com/josdejong/jsoneditor/
    """

    template: str = "json"
    readonly_template: str = "json_readonly"
    style: str = "font-family: monospace;"
    requirements: Tuple[Tuple[str, None], ...] = (("jsoneditor", None),)
    jsonschema = "{}"

    def __init__(self, readonly=False, jsonschema={}, **kw):
        """Initialize instance."""
        self.jsonschema = json.dumps(jsonschema)
        self.title = (jsonschema.get("title", None),)
        self.description = jsonschema.get("description", None)

    def serialize(self, field: Field, cstruct, **kw: Any) -> str:
        """Serialize."""
        try:
            cstruct = json.dumps(cstruct, indent=4)
        except TypeError:
            jsonschema = json.loads(
                kw.get("jsonschema", field.widget.jsonschema)
            )
            if jsonschema.get("type") == "array":
                cstruct = "[]"
            elif jsonschema.get("type") == "object":
                cstruct = "{}"
            else:
                cstruct = "undefined"
        readonly = kw.get("readonly", self.readonly)
        template = readonly and self.readonly_template or self.template
        values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, uuid=uuid4(), **values)

    def deserialize(
        self, field: Field, pstruct: str
    ) -> Union[Dict[str, Any], List[Dict[str, Any]], colander._null]:
        """Deserialize."""
        try:
            return json.loads(pstruct)
        except (TypeError, json.JSONDecodeError):
            return colander.null


class DateTimeNativeWidget(DateTimeInputWidget):
    """Use browser native date time fileds."""

    template = "date_time_native"


class ReactJsonSchemaFormWidget(JsonWidget):
    """Use react-jsonschema-form widget."""

    template = "react-jsonschema-form"
    requirements = (
        ("rjsf-react", None),
        ("rjsf-react-dom", None),
        ("rjsf", None),
    )

    def serialize(self, field: Field, cstruct, **kw: Any) -> str:
        """Serialize with conversion for rjsf."""
        self.get_template_values(field, cstruct, kw)
        kw["jsonschema"] = json.dumps(
            json.loads(kw.get("jsonschema", field.widget.jsonschema)),
            indent=2,
        )
        return super().serialize(field, cstruct, **kw)


class Select2SortableWidget(SelectWidget):
    """Multiselect with ordering.

    Based on http://finn.heemeyer.net/select2.sortable/
    """

    template = "select2sortable"
    readonly_template = "select2sortable_readonly"
    multiple = True
    long_label_generator = None

    style = "font-family: monospace;"
    requirements = (
        ("select2_for_select2sortable", None),
        ("html5sortable_for_select2sortable", None),
        ("select2sortable", None),
    )

    def serialize(self, field, cstruct, **kw):
        """Guarantee order of readonly view."""
        readonly = kw.get("readonly", self.readonly)
        if readonly:
            values = kw.get("values", self.values)
            tmpl_values = self.get_template_values(field, cstruct, kw)
            options = {k: v for k, v in values}
            kw["values"] = [
                (k, options[k])
                for k in tmpl_values["cstruct"] or []
                if k in options
            ]
        return super().serialize(field, cstruct, **kw)


class JExcelObjectArrayWidget(Widget):
    """Array of objects editor in excel like tabular format.

    Based on https://jexcel.net/v3
    """

    template = "jexcel_objectarray"
    readonly_template = "jexcel_objectarray_readonly"
    requirements = (("jexcel", None), ("jsuites", None))
    colander_to_jexcel_mapping = {
        colander.String: dict(type="text", width=150, align="left"),
        colander.Float: dict(
            type="numeric", width=100, mask="[-]#.#", align="right"
        ),
        colander.Number: dict(
            type="numeric", width=100, mask="[-]#.#", align="right"
        ),
        colander.Integer: dict(
            type="numeric", width=100, mask="[-]#", align="right"
        ),
        colander.Int: dict(
            type="numeric", width=100, mask="[-]#", align="right"
        ),
        colander.Boolean: dict(type="checkbox", width=80),
    }

    def __init__(self, readonly=False, jsonschema={}, **kw: Any):
        """Initialize instance."""
        self.jsonschema = jsonschema
        self.title = (jsonschema.get("title", None),)
        self.description = jsonschema.get("description", None)

    def _node_to_colum(self, node):
        """Convert a colander node to a jExcel column."""
        column = {**self.colander_to_jexcel_mapping[node.typ.__class__]}
        if isinstance(getattr(node, "widget"), SelectWidget):
            column["type"] = "dropdown"
            column["source"] = [
                dict(id=id, name=name) for id, name in node.widget.values
            ]
        column["title"] = node.title
        column["field"] = node.name
        column["readOnly"] = self.readonly
        return column

    def serialize(self, field: Field, cstruct, **kw: Any) -> str:
        """Serialize widget.

        Uses json.dumps for serializing
        """
        readonly = kw.get("readonly", self.readonly)
        columns = [
            self._node_to_colum(node) for node in field.children[0].children
        ]
        template = readonly and self.readonly_template or self.template
        values = self.get_template_values(
            field,
            cstruct,
            dict(
                data=json.dumps(
                    cstruct,
                    indent=2,
                    default=lambda x: "" if x == colander.null else str(x),
                ),
                columns=json.dumps(columns, indent=2),
            ),
        )
        return field.renderer(template, uuid=uuid4(), **values)

    def deserialize(
        self, field: Field, pstruct: Union[Dict[str, Any], str]
    ) -> Union[Dict[str, Any], colander._null]:
        """Deserialize."""
        if pstruct in ('""', colander.null):
            return colander.null
        if isinstance(pstruct, dict):
            return pstruct
        try:
            data = json.loads(pstruct)
            if data and isinstance(data, list) and isinstance(data[0], dict):
                return data
            else:
                return colander.null
        except (TypeError, json.JSONDecodeError):
            return colander.null

    def handle_error(self, field, error):
        """Combine error messages."""
        if error.msg:
            field.error = error
        else:
            msgs = ["line %s: %s" % (e.pos + 1, e) for e in error.children]
            field.error = colander.Invalid(field.schema, "\n".join(msgs))


class Select2JsonWidget(Select2Widget):
    """Select from a list of objects."""

    def serialize(
        self, field: Field, cstruct: Union[Dict, colander._null], **kw: Any
    ) -> str:
        """Serialize widget.

        Use json.dump for serializing
        """

        kw["values"] = [
            (json.dumps(v[0]), v[1]) for v in kw.get("values", self.values)
        ]
        return super().serialize(field, cstruct, **kw)

    def deserialize(
        self, field: Field, pstruct: Union[Dict[str, Any], str]
    ) -> Union[Dict[str, Any], colander._null]:
        """Deserialize."""
        if pstruct in ('""', colander.null, self.null_value):
            return colander.null
        if isinstance(pstruct, dict):
            return pstruct
        try:
            return json.loads(pstruct)
        except (TypeError, json.JSONDecodeError):
            return colander.null
