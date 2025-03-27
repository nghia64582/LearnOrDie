package MyApp.akka_actor

import akka.actor.ActorRef

import scala.collection.mutable


object ActorService {
  val actorMap: mutable.Map[String, ActorRef] = mutable.Map[String, ActorRef]()

  def register(name: String, ref: ActorRef): Unit = {
    actorMap += (name -> ref)
  }

  def getActorRef(name: String) : ActorRef = {
    actorMap(name)
  }

  def countActor(): Int = {
    actorMap.size
  }
}
