
import java.io.{FileNotFoundException, IOException}
import scala.io.Source
import scala.util.{Try, Success, Failure}

object TryObject {

  def main(args: Array[String]): Unit = {
    method2();
  }

  def method1(): Unit = {
    // try catch block
    try {
      val path = "C:/Users/NghiaVT/IdeaProjects/untitled/src/main/scala/MyApp/file.txt"
      val source = Source.fromFile(path)
      val data = source.mkString
      println(data)
    } catch {
      case e: FileNotFoundException => println("Couldn't find that file.")
      case e: IOException => println("Had an IOException trying to read that file")
      case e: ArithmeticException => println("Arithmetic exception")
    }
  }

  def method2(): Unit = {
    Try {
      println(1 / 0)
    }.recover {
      case e: Throwable => println("Exception by Try: " + e.toString)
    }
  }

  def divide(x: Int, y : Int) : Try[Int] = {
    Try(x / y)
  }

  divide(10, 0) match {
    case Success(value) => println("Success : " + value)
    case Failure(exception) => println("Raise exception : " + exception)
  }
}

