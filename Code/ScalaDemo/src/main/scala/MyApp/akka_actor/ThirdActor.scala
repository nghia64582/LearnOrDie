package MyApp.akka_actor

import akka.actor.Actor

import scala.util.Random


class ThirdActor() extends Actor {

  override def receive: Receive = {
    case timestamp: Long => {
      val rd:Random = Random()
      println(System.nanoTime() - timestamp)
    }
  }

}
