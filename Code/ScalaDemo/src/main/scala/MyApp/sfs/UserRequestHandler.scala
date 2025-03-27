package MyApp.sfs

import com.smartfoxserver.v2.entities.User
import com.smartfoxserver.v2.entities.data.{ISFSObject, SFSObject}
import com.smartfoxserver.v2.extensions.BaseClientRequestHandler

class UserRequestHandler extends BaseClientRequestHandler {

  override def handleClientRequest(user: User, isfsObject: ISFSObject): Unit = {
    val message = isfsObject.getUtfString("message")

    val responseMessage = s"Server receive: $message"

    val responseParam = SFSObject.newInstance()
    responseParam.putUtfString("response", responseMessage)

    send("response message", responseParam, user)
  }

}
