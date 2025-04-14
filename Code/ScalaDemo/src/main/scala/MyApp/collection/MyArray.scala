package MyApp.collection

import scala.collection.mutable.*;

object MyArray {

  def main(args: Array[String]): Unit = {
    testList()
  }

  def testList(): Unit = {
    // Init LinkedList (flexible size)
    val arr = new ListBuffer[Int]
    arr.addOne(1)
    arr.addOne(2)
    for (i <- arr.indices) {
      print(s"${arr.apply(i)}, ")
    }
  }

  def testArray(): Unit = {
    // init array (fixed size)
    val arr = new Array[Int](10)

    // update value of index
    arr.update(2, 3)
    arr.update(1, 2)
    arr.update(0, 1)

    for (i <- arr.indices) {
      print(s"${arr.apply(i)}, ")
    }
  }

  def testVector(): Unit = {

  }

  def testArrayBuffer(): Unit = {

  }

  def testSet(): Unit = {

  }

  def testMap(): Unit = {

  }

}