# aiaibot

## How to start

1. generate project using `nb create` .
2. create your plugin using `nb plugin create` .
3. writing your plugins under `aiaibot/plugins` folder.
4. run your bot using `nb run --reload` .

## Documentation

See [Docs](https://nonebot.dev/)

群图片bot使用指南：
          1.上传的基本操作为：先引用所需上传的图片（支持上传一条信息里的多张图片），然后输入：存图 名称。\
          例如：存图 相羽爱奈（如有其他名称如：aiai，则可写为：存图 aiai）\
          2.在上传前请注意，发送如下指令：所有文件夹，以查询所要上传的nsy图片文件夹是否存在（所有文件夹均以声优本名命名）。\
          若不存在，则需在第一次上传该女声优图片时，名称填写为nsy的本名，bot将会创建相应的文件夹，例如：存图 相羽爱奈。\
          若存在，则支持使用nsy别名进行上传，例如：存图 aiai（aiai为已写入的相羽爱奈本名）。\
          3.别名查询方法，输入命令：其他 要查询的文件夹名，例如：其他 相羽爱奈\
          4.增加别名，输入命令：其他名称 文件夹名 其他名称，例如：其他 相羽爱奈 aiai\
          5。查询图片，支持本名和别名查询，直接输入，bot会随机从图片库选取图片并发送。\
          tips：上传女声优图片时，如果bot返回信息中，存到的文件夹名称不是女声优本名而是输入的别名，则表示新创建了一个文件夹。不要慌张，请及时联系@Tano，我会及时处理。\
          特别感谢@相羽友希奈·噶吃·凑爱奈为丰富图片库做出的努力！！！\