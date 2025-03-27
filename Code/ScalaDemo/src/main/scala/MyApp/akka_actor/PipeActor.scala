package MyApp.akka_actor

import akka.pattern.pipe
import akka.actor.{Actor, ActorRef, ActorSystem, Props}

import scala.concurrent.Future
import scala.concurrent.ExecutionContext.Implicits.global // Import the implicit ExecutionContext

case object DoSomething

class PipeActor extends Actor {
  def receive: Receive = {
    case DoSomething =>
      val futureResult = doSomethingAsync() // Wrap the operation in a Future
      futureResult pipeTo sender() // Pipe the result to the sender
    case _ => println("Unknown message")
  }

  private def doSomethingAsync(): Future[String] = {
    // Simulate an asynchronous operation
    Future {
      Thread.sleep(1000)
      "Result of the operation"
    }
  }
}

object Main extends App {

  // create actor system
  val system = ActorSystem("actorSystem")

  // create an MyActor using ActorRef
  val pipeActor: ActorRef = system.actorOf(Props[PipeActor](), name = "pipeActor")

  ActorService.register("pipeActor", pipeActor)
  pipeActor ! DoSomething

  // shutdown system
//  system.terminate()
}