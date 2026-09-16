from lxml import etree


def apply(arch, fields_to_hide=None, message=None):
    """Oculta campos de una vista mediante etree de forma no destructiva."""
    try:
        if not isinstance(arch, (etree._Element, etree._ElementTree)):
            root = etree.fromstring(arch if isinstance(arch, (bytes, str)) else b'<form/>')
        else:
            root = arch
        fields_to_hide = fields_to_hide or []
        for field in fields_to_hide:
            nodes = root.iter('field')
            for node in nodes:
                if node.get('name') == field:
                    node.set('invisible', '1')
        return arch if isinstance(arch, (etree._Element, etree._ElementTree)) else etree.tostring(root)
    except Exception:
        return arch