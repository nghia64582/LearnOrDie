package MyApp

object MyApp {
  def main(args: Array[String]): Unit = {
    println("123")
    val PATH: String = "C:/Users/NghiaVT/IdeaProjects/untitled/src/main/scala/MyApp/file.txt"
    val lines = scala.io.Source.fromFile(PATH).mkString
    val isFalse = true
    val nFloat = 1.23

    for (i <- 0 to 10) {
      println(i)
    }
    for (line <- lines) {
      println("Lines " + line)
    }
  }
}
