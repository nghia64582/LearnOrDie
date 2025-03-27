package MyApp.akka_actor

import akka.actor.{Actor, ActorRef}

import scala.collection.mutable

case object GetSize

class SecondActor(firstActor: ActorRef) extends Actor {

  val a: mutable.Map[Int, Int] = mutable.Map[Int, Int]()

  override def receive: Receive = {
    case "a" => println(System.currentTimeMillis().toString + " : a")
    case "b" => println(System.currentTimeMillis().toString + " : b")
    case "c" => println(System.currentTimeMillis().toString + " : c")
    case "d" => println(System.currentTimeMillis().toString + " : d")
    case GetSize => println("Second actor receive getSize, size : " + a.size)
    case Pair(k, v) => {
      println("Key : " + k + " value : " + v)
      a.put(k, v)
    }

  }

}
