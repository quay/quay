from .globalmessages_models_interface import GlobalMessageDataInterface, GlobalMessage
from data import model


class GlobalMessagePreOCI(GlobalMessageDataInterface):
    def get_all_messages(self):
        messages = model.message.get_messages()
        return [self._message(m) for m in messages]

    def create_message(self, severity, media_type_name, content):
        message = {"severity": severity, "media_type": media_type_name, "content": content}
        messages = model.message.create([message])
        return self._message(messages[0])

    def delete_message(self, uuid):
        model.message.delete_message([uuid])

    def _message(self, message_obj):
        if message_obj is None:
            return None
        return GlobalMessage(
            uuid=message_obj.uuid,
            content=message_obj.content,
            severity=message_obj.severity,
            media_type_name=message_obj.media_type.name,
        )


pre_oci_model = GlobalMessagePreOCI()
