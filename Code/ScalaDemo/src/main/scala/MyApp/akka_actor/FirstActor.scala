package MyApp.akka_actor

import akka.actor.Actor

import scala.collection.mutable

class FirstActor extends Actor {

  private val A: Int = 1
  private val B: Int = 2
  private val C: Int = 3
  private val a: mutable.Map[Int, Int] = mutable.Map[Int, Int]()

  override def receive: Receive = {
    case "require name" => println()
    case B => println()
    case C => a += (1 -> 2)
    case message => println("The message is " + message)
  }
}
