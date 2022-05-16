class TemplateNotExists(KeyError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class TemplateAlreadyExists(KeyError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class DeviceNotExists(KeyError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class DeviceAlreadyExists(KeyError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class DataTemplateMismatch(KeyError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class ConnectionNotNecessary(ConnectionError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error
