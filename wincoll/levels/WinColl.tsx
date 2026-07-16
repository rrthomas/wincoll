<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.2" name="WinColl" tilewidth="16" tileheight="16" tilecount="13" columns="0">
 <grid orientation="orthogonal" width="1" height="1"/>
 <tile id="9" type="empty">
  <image width="16" height="16" source="Gap.png"/>
 </tile>
 <tile id="10" type="brick">
  <properties>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Brick.png"/>
 </tile>
 <tile id="11" type="safe">
  <properties>
   <property name="scoring" type="bool" value="true"/>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Safe.png"/>
 </tile>
 <tile id="12" type="diamond">
  <properties>
   <property name="rounded_left" type="bool" value="true"/>
   <property name="rounded_right" type="bool" value="true"/>
   <property name="scoring" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Diamond.png"/>
 </tile>
 <tile id="13" type="blob">
  <properties>
   <property name="rounded_left" type="bool" value="true"/>
   <property name="rounded_right" type="bool" value="true"/>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Blob.png"/>
 </tile>
 <tile id="14" type="earth">
  <image width="16" height="16" source="Earth.png"/>
 </tile>
 <tile id="15" type="rock">
  <properties>
   <property name="rounded_left" type="bool" value="true"/>
   <property name="rounded_right" type="bool" value="true"/>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Rock.png"/>
 </tile>
 <tile id="16" type="key">
  <properties>
   <property name="rounded_left" type="bool" value="true"/>
   <property name="rounded_right" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="Key.png"/>
 </tile>
 <tile id="17" type="hero">
  <image width="16" height="16" source="Hero.png"/>
 </tile>
 <tile id="18" type="top_left_brick">
  <properties>
   <property name="rounded_left" type="bool" value="true"/>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="TopLeftBrick.png"/>
 </tile>
 <tile id="19" type="top_right_brick">
  <properties>
   <property name="rounded_right" type="bool" value="true"/>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="TopRightBrick.png"/>
 </tile>
 <tile id="20" type="bottom_left_brick">
  <properties>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="BottomLeftBrick.png"/>
 </tile>
 <tile id="21" type="bottom_right_brick">
  <properties>
   <property name="solid" type="bool" value="true"/>
  </properties>
  <image width="16" height="16" source="BottomRightBrick.png"/>
 </tile>
</tileset>
