package MyApp.lazy_val

object Example {

  private def task1(): Unit = {
    // define a value based on a function
    // val will be calculated for only one time when it's defined
    var c: Int = 0
    val x = {
      println("x");
      c += 1
      c
    }
    println(x)
    println(x)
  }

  private def task2(): Unit = {
    var c: Int = 0
    // define a lazy val
    // the value will be calculated for the first time it's called
    // then reuse previous value
    lazy val y = {
      println("y");
      c += 1
      c
    }
    println(y)
    println(y)
  }

  private def task3(): Unit = {
    // define a method
    // value will be calculated each time it's called
    var c: Int = 0
    def z = {
      c += 1
      c
    }
    println(z)
    println(z)
  }

  def main(args: Array[String]): Unit = {
    task1();
    task2();
    task3();
  }
}
