package MyApp.data_type

import scala.collection.mutable
import scala.collection.mutable.{ArrayBuffer, HashMap, HashSet, ListBuffer}

object MyDataType {
  val a: Int = 1
  val b: Boolean = false
  val c: Float = 2.3
  val d: List[String] = List("a", "b")

  def main(args: Array[String]) : Unit = {
    println(a * 2)
    println(!b)
    println(Math.floor(c))

    // mutable collection (able to Add, Update, Delete)
    val col1 = ArrayBuffer[Int]()
    col1.addOne(1)
    col1.addOne(2)
    println(col1.size)
    println("Col1 : " + col1)

    val col2 = ListBuffer[Int]()
    col2.addOne(1)
    col2.addOne(2)
    col2.addOne(3)
    col2.addOne(4)
    col2.addOne(5)
    println("Col2 : " + col2)
    println("Col2 : " + col2.find(isEven))

    val col3 = mutable.HashSet[Int]()
    col3.add(1)
    col3.add(1)
    col3.add(2)
    println("Col3 : " + col3)

    val col4 = mutable.HashMap[Int, Int]()
    col4.put(1, 2)
    col4.put(2, 4)
    println("Col4 : " + col4)

    // immutable collection (unable to Create, Update, Delete)
    val set1 = List()
    val set2 = Vector()
    val set3 = Set()
    val set4 = Map()
    val set5 = Tuple()
    
    val e = (1, 2)
  }

  def isEven(x: Int) : Boolean = {
    return x % 2 == 0
  }

}
