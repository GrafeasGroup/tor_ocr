class OCRError(Exception):
    CODES = {
        1: 'success',
        0: 'file not found',
        -10: 'OCR engine parse error',
        -20: 'timeout',
        -30: 'validation error',
        -99: 'UNKNOWN ERROR',
        3: 'File failed validation',  # This is not documented, beware!
    }

    def __init__(self, result):
        super(self.__class__, self).__init__(self.CODES[result['exit_code']])
        self.result = result